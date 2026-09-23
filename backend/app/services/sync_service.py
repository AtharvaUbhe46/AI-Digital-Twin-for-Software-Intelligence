import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.project import (
    Project,
    Contributor,
    Commit,
    Issue,
    PullRequest,
    Release,
    Branch,
    ProjectEvent,
)
from app.services.github_service import github_service

logger = logging.getLogger("digital_twin.sync")


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        # Handle Z and ISO formats
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def calculate_repository_health_index(
    commits: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    pull_requests: List[Dict[str, Any]],
    contributors: List[Dict[str, Any]],
    stars_count: int,
    open_issues_count: int,
) -> Dict[str, Any]:
    """
    Transparent and deterministic Repository Health Index calculation.
    Combines 4 measurable pillars (25 pts each = 100 pts max):
    1. Commit Velocity & Recency (25%)
    2. Issue Health & Resolution (25%)
    3. PR Integration Velocity (25%)
    4. Contributor & Community Vitality (25%)
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # 1. Commit Velocity & Recency (25 pts)
    recent_commits = 0
    latest_commit_date = None
    for c in commits:
        commit_date_str = c.get("commit", {}).get("author", {}).get("date")
        dt = parse_iso_datetime(commit_date_str)
        if dt:
            if latest_commit_date is None or dt > latest_commit_date:
                latest_commit_date = dt
            if dt >= thirty_days_ago:
                recent_commits += 1

    if recent_commits >= 20:
        c1_score = 25.0
        c1_status = "Optimal"
    elif recent_commits >= 5:
        c1_score = 15.0 + (recent_commits - 5) * (10.0 / 15.0)
        c1_status = "Active"
    elif recent_commits >= 1:
        c1_score = 10.0
        c1_status = "Moderate"
    elif latest_commit_date and (now - latest_commit_date).days < 90:
        c1_score = 5.0
        c1_status = "Low Activity"
    else:
        c1_score = 2.0
        c1_status = "Stale"

    # 2. Issue Resolution Ratio (25 pts)
    closed_issues = sum(1 for i in issues if i.get("state") == "closed")
    open_issues_sample = sum(1 for i in issues if i.get("state") == "open")
    total_issues_sample = closed_issues + open_issues_sample

    if total_issues_sample > 0:
        ratio = closed_issues / total_issues_sample
        c2_score = round(ratio * 25.0, 1)
        c2_status = f"{round(ratio * 100)}% resolved"
    elif open_issues_count == 0:
        c2_score = 22.0
        c2_status = "Zero open issues"
    else:
        c2_score = 15.0
        c2_status = "Moderate backlog"

    # 3. PR Integration Velocity (25 pts)
    merged_prs = sum(1 for pr in pull_requests if pr.get("merged_at") is not None)
    closed_prs = sum(1 for pr in pull_requests if pr.get("state") == "closed")
    total_prs = len(pull_requests)

    if total_prs > 0:
        # High merge rate indicates healthy collaboration
        merge_ratio = merged_prs / total_prs if total_prs > 0 else 0.5
        c3_score = round(max(5.0, min(25.0, merge_ratio * 25.0)), 1)
        c3_status = f"{round(merge_ratio * 100)}% merge rate"
    else:
        c3_score = 18.0
        c3_status = "Direct push workflow"

    # 4. Contributor & Community Vitality (25 pts)
    contrib_count = len(contributors)
    if contrib_count >= 15:
        contrib_pts = 15.0
    elif contrib_count >= 5:
        contrib_pts = 10.0 + (contrib_count - 5) * 0.5
    else:
        contrib_pts = max(3.0, contrib_count * 2.0)

    # Stars bonus (up to 10 pts)
    if stars_count >= 1000:
        stars_pts = 10.0
    elif stars_count >= 100:
        stars_pts = 7.0
    elif stars_count >= 10:
        stars_pts = 4.0
    else:
        stars_pts = 2.0

    c4_score = min(25.0, contrib_pts + stars_pts)
    c4_status = f"{contrib_count} contributors, {stars_count} stars"

    total_health = round(c1_score + c2_score + c3_score + c4_score, 1)

    return {
        "score": total_health,
        "formula": "Repository Health Index = Commit Velocity (25%) + Issue Resolution (25%) + PR Merge Velocity (25%) + Contributor Vitality (25%)",
        "components": [
            {
                "name": "Commit Velocity & Recency",
                "weight": "25%",
                "score": round(c1_score, 1),
                "max_score": 25.0,
                "detail": f"{recent_commits} commits in last 30d ({c1_status})"
            },
            {
                "name": "Issue Resolution Ratio",
                "weight": "25%",
                "score": round(c2_score, 1),
                "max_score": 25.0,
                "detail": f"{closed_issues} closed / {total_issues_sample} sampled ({c2_status})"
            },
            {
                "name": "PR Merge Velocity",
                "weight": "25%",
                "score": round(c3_score, 1),
                "max_score": 25.0,
                "detail": f"{merged_prs} merged PRs ({c3_status})"
            },
            {
                "name": "Community & Contributor Vitality",
                "weight": "25%",
                "score": round(c4_score, 1),
                "max_score": 25.0,
                "detail": c4_status
            }
        ]
    }


class SyncService:
    @staticmethod
    async def sync_repository(project_id: int, db: Session) -> Project:
        """
        Synchronizes a project with live data from GitHub API.
        Persists normalized entities into PostgreSQL.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} does not exist.")

        project.status = "syncing"
        db.commit()

        owner = project.github_owner
        repo = project.github_repo
        logger.info(f"Starting GitHub synchronization for {owner}/{repo} (ID: {project_id})...")

        try:
            # 1. Fetch Repo Metadata
            meta = await github_service.get_repo_details(owner, repo)
            project.name = meta.get("name", repo)
            project.description = meta.get("description")
            project.html_url = meta.get("html_url", project.html_url)
            project.default_branch = meta.get("default_branch", "main")
            project.language = meta.get("language")
            project.visibility = meta.get("visibility", "public")
            project.stars_count = meta.get("stargazers_count", 0)
            project.forks_count = meta.get("forks_count", 0)
            project.watchers_count = meta.get("subscribers_count", 0)
            project.open_issues_count = meta.get("open_issues_count", 0)
            project.network_count = meta.get("network_count", 0)
            project.subscribers_count = meta.get("subscribers_count", 0)

            license_info = meta.get("license")
            if license_info and isinstance(license_info, dict):
                project.license_name = license_info.get("spdx_id") or license_info.get("name")

            project.repo_created_at = parse_iso_datetime(meta.get("created_at"))
            project.repo_updated_at = parse_iso_datetime(meta.get("updated_at"))
            project.repo_pushed_at = parse_iso_datetime(meta.get("pushed_at"))

            # 2. Fetch Contributors
            raw_contribs = await github_service.get_contributors(owner, repo, per_page=30)
            db.query(Contributor).filter(Contributor.project_id == project_id).delete()
            for c in raw_contribs:
                contrib = Contributor(
                    project_id=project_id,
                    github_id=c.get("id"),
                    login=c.get("login", "unknown"),
                    avatar_url=c.get("avatar_url"),
                    html_url=c.get("html_url"),
                    contributions=c.get("contributions", 0),
                    contributor_type=c.get("type", "User")
                )
                db.add(contrib)

            # 3. Fetch Commits
            raw_commits = await github_service.get_commits(owner, repo, per_page=50)
            db.query(Commit).filter(Commit.project_id == project_id).delete()
            for cm in raw_commits:
                commit_info = cm.get("commit", {})
                author_info = commit_info.get("author", {})
                gh_author = cm.get("author") or {}
                commit_obj = Commit(
                    project_id=project_id,
                    sha=cm.get("sha", "")[:40],
                    message=commit_info.get("message", "").split("\n")[0][:500],
                    author_name=author_info.get("name"),
                    author_email=author_info.get("email"),
                    author_date=parse_iso_datetime(author_info.get("date")),
                    author_login=gh_author.get("login"),
                    author_avatar_url=gh_author.get("avatar_url"),
                    html_url=cm.get("html_url")
                )
                db.add(commit_obj)

            # 4. Fetch Pull Requests
            raw_prs = await github_service.get_pull_requests(owner, repo, state="all", per_page=50)
            db.query(PullRequest).filter(PullRequest.project_id == project_id).delete()
            open_pr_count = 0
            for pr in raw_prs:
                if pr.get("state") == "open":
                    open_pr_count += 1
                pr_user = pr.get("user") or {}
                pr_obj = PullRequest(
                    project_id=project_id,
                    github_id=pr.get("id"),
                    number=pr.get("number", 0),
                    title=pr.get("title", "")[:500],
                    state=pr.get("state", "open"),
                    author_login=pr_user.get("login"),
                    author_avatar_url=pr_user.get("avatar_url"),
                    is_merged=pr.get("merged_at") is not None,
                    draft=pr.get("draft", False),
                    created_at=parse_iso_datetime(pr.get("created_at")),
                    updated_at=parse_iso_datetime(pr.get("updated_at")),
                    merged_at=parse_iso_datetime(pr.get("merged_at")),
                    closed_at=parse_iso_datetime(pr.get("closed_at")),
                    html_url=pr.get("html_url")
                )
                db.add(pr_obj)
            project.open_prs_count = open_pr_count

            # 5. Fetch Issues (excluding PRs)
            raw_issues = await github_service.get_issues(owner, repo, state="all", per_page=50)
            db.query(Issue).filter(Issue.project_id == project_id).delete()
            for iss in raw_issues:
                iss_user = iss.get("user") or {}
                labels = [l.get("name") for l in iss.get("labels", []) if isinstance(l, dict)]
                issue_obj = Issue(
                    project_id=project_id,
                    github_id=iss.get("id"),
                    number=iss.get("number", 0),
                    title=iss.get("title", "")[:500],
                    state=iss.get("state", "open"),
                    author_login=iss_user.get("login"),
                    author_avatar_url=iss_user.get("avatar_url"),
                    labels=labels,
                    comments_count=iss.get("comments", 0),
                    created_at=parse_iso_datetime(iss.get("created_at")),
                    closed_at=parse_iso_datetime(iss.get("closed_at")),
                    html_url=iss.get("html_url")
                )
                db.add(issue_obj)

            # 6. Fetch Releases
            raw_releases = await github_service.get_releases(owner, repo, per_page=20)
            db.query(Release).filter(Release.project_id == project_id).delete()
            for rel in raw_releases:
                rel_author = rel.get("author") or {}
                rel_obj = Release(
                    project_id=project_id,
                    github_id=rel.get("id"),
                    tag_name=rel.get("tag_name", "v0.0.0"),
                    name=rel.get("name") or rel.get("tag_name"),
                    author_login=rel_author.get("login"),
                    published_at=parse_iso_datetime(rel.get("published_at")),
                    html_url=rel.get("html_url"),
                    is_prerelease=rel.get("prerelease", False)
                )
                db.add(rel_obj)

            # 7. Fetch Branches
            raw_branches = await github_service.get_branches(owner, repo, per_page=30)
            db.query(Branch).filter(Branch.project_id == project_id).delete()
            for br in raw_branches:
                commit_info = br.get("commit") or {}
                branch_obj = Branch(
                    project_id=project_id,
                    name=br.get("name", "main"),
                    commit_sha=commit_info.get("sha"),
                    is_protected=br.get("protected", False),
                    is_default=(br.get("name") == project.default_branch)
                )
                db.add(branch_obj)

            # 8. Derive Recent Events
            db.query(ProjectEvent).filter(ProjectEvent.project_id == project_id).delete()
            events_to_add: List[ProjectEvent] = []

            for cm in raw_commits[:10]:
                author_login = (cm.get("author") or {}).get("login") or cm.get("commit", {}).get("author", {}).get("name")
                events_to_add.append(ProjectEvent(
                    project_id=project_id,
                    event_type="commit",
                    title=f"Commit: {cm.get('commit', {}).get('message', '').splitlines()[0][:120]}",
                    actor_login=author_login,
                    actor_avatar_url=(cm.get("author") or {}).get("avatar_url"),
                    event_time=parse_iso_datetime(cm.get("commit", {}).get("author", {}).get("date")),
                    html_url=cm.get("html_url")
                ))

            for pr in raw_prs[:10]:
                event_type = "pr_merge" if pr.get("merged_at") else ("pr_open" if pr.get("state") == "open" else "pr_close")
                events_to_add.append(ProjectEvent(
                    project_id=project_id,
                    event_type=event_type,
                    title=f"PR #{pr.get('number')}: {pr.get('title')[:120]}",
                    actor_login=(pr.get("user") or {}).get("login"),
                    actor_avatar_url=(pr.get("user") or {}).get("avatar_url"),
                    event_time=parse_iso_datetime(pr.get("merged_at") or pr.get("created_at")),
                    html_url=pr.get("html_url")
                ))

            for iss in raw_issues[:10]:
                event_type = "issue_close" if iss.get("state") == "closed" else "issue_open"
                events_to_add.append(ProjectEvent(
                    project_id=project_id,
                    event_type=event_type,
                    title=f"Issue #{iss.get('number')}: {iss.get('title')[:120]}",
                    actor_login=(iss.get("user") or {}).get("login"),
                    actor_avatar_url=(iss.get("user") or {}).get("avatar_url"),
                    event_time=parse_iso_datetime(iss.get("closed_at") or iss.get("created_at")),
                    html_url=iss.get("html_url")
                ))

            for rel in raw_releases[:5]:
                events_to_add.append(ProjectEvent(
                    project_id=project_id,
                    event_type="release",
                    title=f"Release {rel.get('tag_name')}: {rel.get('name') or rel.get('tag_name')}",
                    actor_login=(rel.get("author") or {}).get("login"),
                    actor_avatar_url=(rel.get("author") or {}).get("avatar_url"),
                    event_time=parse_iso_datetime(rel.get("published_at")),
                    html_url=rel.get("html_url")
                ))

            # Filter valid event times and sort descending
            events_to_add = [e for e in events_to_add if e.event_time is not None]
            events_to_add.sort(key=lambda x: x.event_time, reverse=True)
            for ev in events_to_add[:25]:
                db.add(ev)

            # 9. Calculate Repository Health Index
            health_calc = calculate_repository_health_index(
                commits=raw_commits,
                issues=raw_issues,
                pull_requests=raw_prs,
                contributors=raw_contribs,
                stars_count=project.stars_count,
                open_issues_count=project.open_issues_count,
            )
            project.health_score = health_calc["score"]
            project.health_index_details = health_calc

            project.last_synced_at = datetime.now(timezone.utc)
            project.status = "synced"
            db.commit()
            db.refresh(project)
            logger.info(f"Successfully synchronized {owner}/{repo}. Health Score: {project.health_score}")
            return project

        except Exception as exc:
            db.rollback()
            project.status = "error"
            try:
                db.commit()
            except Exception:
                pass
            logger.error(f"Error synchronizing repository {owner}/{repo}: {exc}", exc_info=True)
            raise


sync_service = SyncService()
