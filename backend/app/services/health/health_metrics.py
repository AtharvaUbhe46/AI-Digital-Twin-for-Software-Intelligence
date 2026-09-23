from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.project import Commit, Issue, PullRequest, Release, Contributor
from app.models.digital_twin import RepositoryFile, DigitalTwinChange
from app.core.config import settings


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is UTC-aware for safe subtraction."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_activity_metrics(project_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes repository activity metrics based on commits and timestamps.
    """
    now = datetime.now(timezone.utc)
    window_days = settings.HEALTH_RECENT_DAYS
    window_start = now - timedelta(days=window_days)

    commits = db.query(Commit).filter(Commit.project_id == project_id).order_by(desc(Commit.author_date)).all()
    total_commits = len(commits)

    if total_commits == 0:
        return {
            "has_data": False,
            "total_commits": 0,
            "reason": "No commits have been synchronized for this repository yet.",
        }

    latest_commit = commits[0]
    latest_date = ensure_utc(latest_commit.author_date)
    days_since_last_commit = (now - latest_date).days if latest_date else 999
    days_since_last_commit = max(0, days_since_last_commit)

    recent_commits = [c for c in commits if ensure_utc(c.author_date) and ensure_utc(c.author_date) >= window_start]
    recent_commit_count = len(recent_commits)

    recent_authors = {c.author_login or c.author_email for c in recent_commits if c.author_login or c.author_email}
    active_contributors_recent = len(recent_authors)

    # Weekly commit frequency in recent window
    weeks = max(1.0, window_days / 7.0)
    commits_per_week = round(recent_commit_count / weeks, 2)

    return {
        "has_data": True,
        "total_commits": total_commits,
        "recent_commits": recent_commit_count,
        "recent_window_days": window_days,
        "active_contributors_recent": active_contributors_recent,
        "days_since_last_commit": days_since_last_commit,
        "latest_commit_date": latest_date.isoformat() if latest_date else None,
        "commits_per_week": commits_per_week,
        "latest_commit_sha": latest_commit.sha[:8] if latest_commit.sha else None,
    }


def compute_issue_metrics(project_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes issue health metrics based on open/closed status, age, and staleness.
    """
    now = datetime.now(timezone.utc)
    window_days = settings.HEALTH_RECENT_DAYS
    stale_days = settings.HEALTH_STALE_ISSUE_DAYS
    window_start = now - timedelta(days=window_days)

    issues = db.query(Issue).filter(Issue.project_id == project_id).all()
    total_issues = len(issues)

    if total_issues == 0:
        return {
            "has_data": False,
            "total_issues": 0,
            "reason": "No issues synchronized or repository has issue tracking disabled.",
        }

    open_issues = [i for i in issues if i.state == "open"]
    closed_issues = [i for i in issues if i.state == "closed"]

    total_open = len(open_issues)
    total_closed = len(closed_issues)

    # Issues opened & closed in recent window
    opened_recent = sum(1 for i in issues if ensure_utc(i.created_at) and ensure_utc(i.created_at) >= window_start)
    closed_recent = sum(1 for i in closed_issues if ensure_utc(i.closed_at) and ensure_utc(i.closed_at) >= window_start)

    closure_rate = round((closed_recent / opened_recent) * 100.0, 1) if opened_recent > 0 else (100.0 if total_open == 0 else 0.0)

    # Calculate ages of open issues
    open_ages: List[int] = []
    stale_issues: List[Dict[str, Any]] = []

    for issue in open_issues:
        c_at = ensure_utc(issue.created_at)
        if c_at:
            age = max(0, (now - c_at).days)
            open_ages.append(age)
            if age >= stale_days:
                stale_issues.append({
                    "number": issue.number,
                    "title": issue.title,
                    "age_days": age,
                    "html_url": issue.html_url,
                })

    avg_age_days = round(sum(open_ages) / len(open_ages), 1) if open_ages else 0.0
    oldest_age_days = max(open_ages) if open_ages else 0
    stale_count = len(stale_issues)
    stale_ratio = round((stale_count / total_open) * 100.0, 1) if total_open > 0 else 0.0

    return {
        "has_data": True,
        "total_issues": total_issues,
        "total_open": total_open,
        "total_closed": total_closed,
        "opened_recent": opened_recent,
        "closed_recent": closed_recent,
        "closure_rate": closure_rate,
        "avg_age_days": avg_age_days,
        "oldest_age_days": oldest_age_days,
        "stale_count": stale_count,
        "stale_threshold_days": stale_days,
        "stale_ratio": stale_ratio,
        "stale_samples": stale_issues[:5],
    }


def compute_pr_metrics(project_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes pull request health metrics including merge rate, review age, and staleness.
    """
    now = datetime.now(timezone.utc)
    window_days = settings.HEALTH_RECENT_DAYS
    stale_days = settings.HEALTH_STALE_PR_DAYS
    window_start = now - timedelta(days=window_days)

    prs = db.query(PullRequest).filter(PullRequest.project_id == project_id).all()
    total_prs = len(prs)

    if total_prs == 0:
        return {
            "has_data": False,
            "total_prs": 0,
            "reason": "No pull requests synchronized for this repository.",
        }

    open_prs = [p for p in prs if p.state == "open"]
    merged_prs = [p for p in prs if p.is_merged or (p.merged_at is not None)]
    closed_prs = [p for p in prs if p.state == "closed" and not p.is_merged]

    total_open = len(open_prs)
    total_merged = len(merged_prs)

    # PRs opened and merged in recent window
    opened_recent = sum(1 for p in prs if ensure_utc(p.created_at) and ensure_utc(p.created_at) >= window_start)
    merged_recent = sum(1 for p in merged_prs if ensure_utc(p.merged_at) and ensure_utc(p.merged_at) >= window_start)

    merge_rate = round((merged_recent / opened_recent) * 100.0, 1) if opened_recent > 0 else (100.0 if total_open == 0 else 0.0)

    # Open PR ages
    open_ages: List[int] = []
    stale_prs: List[Dict[str, Any]] = []

    for pr in open_prs:
        c_at = ensure_utc(pr.created_at)
        if c_at:
            age = max(0, (now - c_at).days)
            open_ages.append(age)
            if age >= stale_days:
                stale_prs.append({
                    "number": pr.number,
                    "title": pr.title,
                    "age_days": age,
                    "html_url": pr.html_url,
                })

    avg_age_days = round(sum(open_ages) / len(open_ages), 1) if open_ages else 0.0
    oldest_age_days = max(open_ages) if open_ages else 0
    stale_count = len(stale_prs)
    stale_ratio = round((stale_count / total_open) * 100.0, 1) if total_open > 0 else 0.0

    return {
        "has_data": True,
        "total_prs": total_prs,
        "total_open": total_open,
        "total_merged": total_merged,
        "opened_recent": opened_recent,
        "merged_recent": merged_recent,
        "merge_rate": merge_rate,
        "avg_age_days": avg_age_days,
        "oldest_age_days": oldest_age_days,
        "stale_count": stale_count,
        "stale_threshold_days": stale_days,
        "stale_ratio": stale_ratio,
        "stale_samples": stale_prs[:5],
    }


def compute_contributor_metrics(project_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes contributor activity and concentration indicators.
    """
    now = datetime.now(timezone.utc)
    window_days = settings.HEALTH_RECENT_DAYS
    window_start = now - timedelta(days=window_days)

    contributors = db.query(Contributor).filter(Contributor.project_id == project_id).all()
    commits = db.query(Commit).filter(Commit.project_id == project_id).all()

    total_contributors = len(contributors)
    total_commits = len(commits)

    if total_contributors == 0 and total_commits == 0:
        return {
            "has_data": False,
            "total_contributors": 0,
            "reason": "No contributor or commit records available.",
        }

    # Group commits by author
    author_counts: Dict[str, int] = {}
    recent_author_counts: Dict[str, int] = {}

    for c in commits:
        author = c.author_login or c.author_email or "unknown"
        author_counts[author] = author_counts.get(author, 0) + 1
        c_date = ensure_utc(c.author_date)
        if c_date and c_date >= window_start:
            recent_author_counts[author] = recent_author_counts.get(author, 0) + 1

    active_contributors_recent = len(recent_author_counts)

    # Top contributor share (using recent if available, otherwise total)
    counts_to_use = recent_author_counts if recent_author_counts else author_counts
    total_to_use = sum(counts_to_use.values())

    if total_to_use > 0:
        sorted_authors = sorted(counts_to_use.items(), key=lambda x: x[1], reverse=True)
        top_contributor_commits = sorted_authors[0][1]
        top_contributor_percentage = round((top_contributor_commits / total_to_use) * 100.0, 1)

        top_3_commits = sum(cnt for _, cnt in sorted_authors[:3])
        top_3_percentage = round((top_3_commits / total_to_use) * 100.0, 1)
        top_author_identifier = sorted_authors[0][0]
    else:
        top_contributor_percentage = 0.0
        top_3_percentage = 0.0
        top_author_identifier = None

    return {
        "has_data": True,
        "total_contributors": max(total_contributors, len(author_counts)),
        "active_contributors_recent": active_contributors_recent,
        "top_contributor_percentage": top_contributor_percentage,
        "top_3_percentage": top_3_percentage,
        "top_author_identifier": top_author_identifier,
        "recent_window_days": window_days,
    }


def compute_release_metrics(project_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes release recency and cadence. Returns has_data=False if no releases.
    """
    now = datetime.now(timezone.utc)
    window_days = settings.HEALTH_RECENT_DAYS
    window_start = now - timedelta(days=window_days)

    releases = db.query(Release).filter(Release.project_id == project_id).order_by(desc(Release.published_at)).all()
    total_releases = len(releases)

    if total_releases == 0:
        return {
            "has_data": False,
            "total_releases": 0,
            "reason": "Repository does not have any tagged GitHub releases published.",
        }

    latest = releases[0]
    latest_date = ensure_utc(latest.published_at)
    days_since_latest = max(0, (now - latest_date).days) if latest_date else 999

    recent_releases = sum(1 for r in releases if ensure_utc(r.published_at) and ensure_utc(r.published_at) >= window_start)

    return {
        "has_data": True,
        "total_releases": total_releases,
        "latest_release_tag": latest.tag_name,
        "latest_release_date": latest_date.isoformat() if latest_date else None,
        "days_since_latest_release": days_since_latest,
        "releases_recent": recent_releases,
    }


def compute_change_stability_metrics(project_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes change stability from Digital Twin tracked files, changes, and commits.
    """
    now = datetime.now(timezone.utc)
    window_days = settings.HEALTH_RECENT_DAYS
    window_start = now - timedelta(days=window_days)

    commits = db.query(Commit).filter(Commit.project_id == project_id).all()
    files_count = db.query(RepositoryFile).filter(RepositoryFile.project_id == project_id).count()

    total_commits = len(commits)
    if total_commits == 0:
        return {
            "has_data": False,
            "reason": "Insufficient commit history for change stability evaluation.",
        }

    recent_commits = [c for c in commits if ensure_utc(c.author_date) and ensure_utc(c.author_date) >= window_start]
    recent_commit_count = len(recent_commits)

    # Baseline: average commits per 30 days historically
    oldest_commit = min((ensure_utc(c.author_date) for c in commits if ensure_utc(c.author_date)), default=None)
    if oldest_commit:
        repo_age_days = max(1, (now - oldest_commit).days)
        historical_baseline_monthly = (total_commits / repo_age_days) * window_days
    else:
        historical_baseline_monthly = max(1.0, float(recent_commit_count))

    activity_ratio = round(recent_commit_count / max(1.0, historical_baseline_monthly), 2)

    return {
        "has_data": True,
        "total_files_tracked": files_count,
        "recent_commit_count": recent_commit_count,
        "historical_baseline_monthly": round(historical_baseline_monthly, 1),
        "activity_ratio": activity_ratio,
        "is_bursty": activity_ratio >= settings.RISK_ACTIVITY_SPIKE_MULTIPLIER,
    }


def compute_maintenance_metrics(project_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes maintenance health combining inactivity, backlogs, and stale entities.
    """
    act = compute_activity_metrics(project_id, db)
    iss = compute_issue_metrics(project_id, db)
    prs = compute_pr_metrics(project_id, db)

    days_since_commit = act.get("days_since_last_commit", 999) if act.get("has_data") else 999
    stale_issues = iss.get("stale_count", 0) if iss.get("has_data") else 0
    stale_prs = prs.get("stale_count", 0) if prs.get("has_data") else 0
    open_issues = iss.get("total_open", 0) if iss.get("has_data") else 0
    open_prs = prs.get("total_open", 0) if prs.get("has_data") else 0

    has_data = act.get("has_data") or iss.get("has_data") or prs.get("has_data")

    return {
        "has_data": has_data,
        "days_since_last_commit": days_since_commit,
        "stale_issues_count": stale_issues,
        "stale_prs_count": stale_prs,
        "open_issues_count": open_issues,
        "open_prs_count": open_prs,
    }
