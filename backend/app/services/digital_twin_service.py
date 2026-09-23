import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.core.config import settings
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
from app.models.digital_twin import (
    DigitalTwin,
    DigitalTwinSnapshot,
    DigitalTwinChange,
    DigitalTwinEvent,
    RepositoryFile,
)
from app.services.github_service import (
    github_service,
    parse_github_url,
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubRepoNotFoundError,
)
from app.services.sync_service import calculate_repository_health_index, parse_iso_datetime

logger = logging.getLogger("digital_twin.core_service")


class DigitalTwinService:
    @staticmethod
    def get_or_create_twin(project_id: int, db: Session) -> DigitalTwin:
        """
        Retrieves the DigitalTwin for a project, creating one in NOT_INITIALIZED
        state if it does not yet exist.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} does not exist.")

        twin = db.query(DigitalTwin).filter(DigitalTwin.project_id == project_id).first()
        if not twin:
            twin = DigitalTwin(
                project_id=project_id,
                current_version=1,
                status="NOT_INITIALIZED",
                stale_threshold_minutes=settings.DIGITAL_TWIN_STALE_MINUTES,
                fidelity_score=0.0,
            )
            db.add(twin)
            db.commit()
            db.refresh(twin)

        return twin

    @staticmethod
    def get_twin_response_data(twin: DigitalTwin) -> Dict[str, Any]:
        """
        Augments DigitalTwin model with dynamic staleness and computed status.
        """
        now = datetime.now(timezone.utc)
        staleness_minutes: Optional[float] = None
        is_outdated = False
        effective_status = twin.status

        if twin.last_synced_at:
            last_synced = twin.last_synced_at
            if last_synced.tzinfo is None:
                last_synced = last_synced.replace(tzinfo=timezone.utc)
            delta = now - last_synced
            staleness_minutes = round(delta.total_seconds() / 60.0, 1)
            if staleness_minutes > twin.stale_threshold_minutes:
                is_outdated = True
                if twin.status == "ACTIVE":
                    effective_status = "OUTDATED"

        return {
            "id": twin.id,
            "project_id": twin.project_id,
            "current_version": twin.current_version,
            "status": effective_status,
            "error_message": twin.error_message,
            "last_synced_at": twin.last_synced_at,
            "fidelity_score": twin.fidelity_score,
            "stale_threshold_minutes": twin.stale_threshold_minutes,
            "is_outdated": is_outdated,
            "staleness_minutes": staleness_minutes,
            "created_at": twin.created_at,
            "updated_at": twin.updated_at,
        }

    @staticmethod
    def _compute_fidelity_score(entity_counts: Dict[str, int]) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Evaluates Digital Twin fidelity based on completeness of tracked repository entities.
        """
        keys = [
            ("commits", "Commits", "git-commit"),
            ("contributors", "Contributors", "users"),
            ("issues", "Issues", "alert-circle"),
            ("pull_requests", "Pull Requests", "git-pull-request"),
            ("branches", "Branches", "git-branch"),
            ("releases", "Releases", "tag"),
            ("files", "Files & Tree", "folder-tree"),
        ]
        components = []
        active_pillars = 0
        for key, label, icon in keys:
            count = entity_counts.get(key, 0)
            if count > 0:
                active_pillars += 1
            components.append({
                "key": key,
                "name": label,
                "synced": count,
                "icon": icon,
                "active": count > 0,
            })

        score = round((active_pillars / len(keys)) * 100.0, 1)
        return score, components

    async def initialize_twin(self, project_id: int, db: Session) -> Dict[str, Any]:
        """
        Initializes the Digital Twin for a repository for the first time.
        Creates version 1 snapshot and records initial twin state.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} does not exist.")

        twin = self.get_or_create_twin(project_id, db)

        existing_snapshot = (
            db.query(DigitalTwinSnapshot)
            .filter(
                DigitalTwinSnapshot.digital_twin_id == twin.id,
                DigitalTwinSnapshot.version == 1
            )
            .first()
        )
        if existing_snapshot:
            logger.info(f"Digital Twin for project {project_id} is already initialized. Running synchronization instead.")
            return await self.synchronize_twin(project_id, db, source="reconnect_sync")

        twin.status = "INITIALIZING"
        twin.error_message = None
        db.commit()

        try:
            return await self._execute_sync(project=project, twin=twin, db=db, is_initial=True, source="initial_sync")
        except Exception as exc:
            db.rollback()
            twin.status = "ERROR"
            twin.error_message = str(exc)
            db.commit()
            logger.error(f"Failed to initialize Digital Twin for project {project_id}: {exc}", exc_info=True)
            raise

    async def synchronize_twin(self, project_id: int, db: Session, source: str = "manual_sync") -> Dict[str, Any]:
        """
        Synchronizes an existing Digital Twin with live repository data.
        Performs change detection, creates snapshots, increments version if state changed,
        and ensures idempotency if no changes occurred.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} does not exist.")

        twin = self.get_or_create_twin(project_id, db)
        twin.status = "SYNCING"
        db.commit()

        try:
            return await self._execute_sync(project=project, twin=twin, db=db, is_initial=False, source=source)
        except Exception as exc:
            db.rollback()
            twin.status = "ERROR"
            twin.error_message = str(exc)
            db.commit()
            logger.error(f"Failed to synchronize Digital Twin for project {project_id}: {exc}", exc_info=True)
            raise

    async def _execute_sync(
        self,
        project: Project,
        twin: DigitalTwin,
        db: Session,
        is_initial: bool,
        source: str = "github_sync"
    ) -> Dict[str, Any]:
        """
        Internal synchronization routine with full Change Detection and State Versioning.
        """
        owner = project.github_owner
        repo = project.github_repo
        now = datetime.now(timezone.utc)
        logger.info(f"Executing Digital Twin sync for {owner}/{repo} (is_initial={is_initial})...")

        # 1. Fetch live GitHub data
        meta = await github_service.get_repo_details(owner, repo)
        raw_commits = await github_service.get_commits(owner, repo, per_page=50)
        raw_contribs = await github_service.get_contributors(owner, repo, per_page=30)
        raw_issues = await github_service.get_issues(owner, repo, state="all", per_page=50)
        raw_prs = await github_service.get_pull_requests(owner, repo, state="all", per_page=50)
        raw_releases = await github_service.get_releases(owner, repo, per_page=20)
        raw_branches = await github_service.get_branches(owner, repo, per_page=30)
        default_branch = meta.get("default_branch", "main")
        raw_tree = await github_service.get_repo_tree(owner, repo, tree_sha=default_branch)

        # 2. Existing entities in database for change detection
        existing_commits = {c.sha: c for c in db.query(Commit).filter(Commit.project_id == project.id).all()}
        existing_contribs = {c.login: c for c in db.query(Contributor).filter(Contributor.project_id == project.id).all()}
        existing_issues = {i.number: i for i in db.query(Issue).filter(Issue.project_id == project.id).all()}
        existing_prs = {p.number: p for p in db.query(PullRequest).filter(PullRequest.project_id == project.id).all()}
        existing_branches = {b.name: b for b in db.query(Branch).filter(Branch.project_id == project.id).all()}
        existing_releases = {r.tag_name: r for r in db.query(Release).filter(Release.project_id == project.id).all()}
        existing_files = {f.path: f for f in db.query(RepositoryFile).filter(RepositoryFile.project_id == project.id).all()}

        detected_changes: List[DigitalTwinChange] = []
        detected_events: List[DigitalTwinEvent] = []
        summary_messages: List[str] = []

        if is_initial:
            # First initialization: Initial state capture
            summary_messages.append(f"Initial Digital Twin snapshot v1 created for {project.full_name}.")
            detected_events.append(DigitalTwinEvent(
                digital_twin_id=twin.id,
                event_type="TWIN_INITIALIZED",
                entity_type="twin",
                entity_id=str(twin.id),
                title=f"Digital Twin Initialized: {project.full_name}",
                description=f"Initialized virtual representation with {len(raw_commits)} commits, {len(raw_contribs)} contributors, {len(raw_prs)} PRs, and {len(raw_issues)} issues.",
                timestamp=now,
                source=source,
                event_metadata={"version": 1, "repository": project.full_name},
            ))
        else:
            # Change detection vs previous state
            # A. Commits
            new_commit_count = 0
            for cm in raw_commits:
                sha = cm.get("sha", "")[:40]
                if sha and sha not in existing_commits:
                    new_commit_count += 1
                    commit_msg = cm.get("commit", {}).get("message", "").split("\n")[0][:100]
                    author_name = cm.get("commit", {}).get("author", {}).get("name") or "Unknown"
                    author_login = (cm.get("author") or {}).get("login")
                    detected_changes.append(DigitalTwinChange(
                        digital_twin_id=twin.id,
                        entity_type="commit",
                        entity_id=sha,
                        change_type="CREATED",
                        change_summary=f"New commit: {commit_msg} by {author_name}",
                        new_value={"sha": sha, "message": commit_msg, "author": author_name},
                        detected_at=now,
                        source=source,
                    ))
                    detected_events.append(DigitalTwinEvent(
                        digital_twin_id=twin.id,
                        event_type="COMMIT_ADDED",
                        entity_type="commit",
                        entity_id=sha,
                        title=f"Commit: {commit_msg}",
                        description=f"Commit {sha[:7]} by {author_name}",
                        timestamp=parse_iso_datetime(cm.get("commit", {}).get("author", {}).get("date")) or now,
                        actor_login=author_login,
                        actor_avatar_url=(cm.get("author") or {}).get("avatar_url"),
                        source=source,
                        event_metadata={"sha": sha, "html_url": cm.get("html_url")},
                    ))
            if new_commit_count > 0:
                summary_messages.append(f"{new_commit_count} new commit(s) detected")

            # B. Issues
            new_issue_count = 0
            closed_issue_count = 0
            for iss in raw_issues:
                num = iss.get("number", 0)
                state = iss.get("state", "open")
                title = iss.get("title", "")[:120]
                user_login = (iss.get("user") or {}).get("login")
                user_avatar = (iss.get("user") or {}).get("avatar_url")
                if num not in existing_issues:
                    new_issue_count += 1
                    detected_changes.append(DigitalTwinChange(
                        digital_twin_id=twin.id,
                        entity_type="issue",
                        entity_id=str(num),
                        change_type="CREATED",
                        change_summary=f"New issue #{num}: {title}",
                        new_value={"number": num, "title": title, "state": state},
                        detected_at=now,
                        source=source,
                    ))
                    detected_events.append(DigitalTwinEvent(
                        digital_twin_id=twin.id,
                        event_type="ISSUE_OPENED",
                        entity_type="issue",
                        entity_id=str(num),
                        title=f"Issue #{num} Opened: {title}",
                        description=f"Issue opened by {user_login}",
                        timestamp=parse_iso_datetime(iss.get("created_at")) or now,
                        actor_login=user_login,
                        actor_avatar_url=user_avatar,
                        source=source,
                        event_metadata={"number": num, "html_url": iss.get("html_url")},
                    ))
                else:
                    prev_state = existing_issues[num].state
                    if prev_state != state:
                        change_type = "STATE_CHANGED"
                        ev_type = "ISSUE_CLOSED" if state == "closed" else "ISSUE_OPENED"
                        if state == "closed":
                            closed_issue_count += 1
                        detected_changes.append(DigitalTwinChange(
                            digital_twin_id=twin.id,
                            entity_type="issue",
                            entity_id=str(num),
                            change_type=change_type,
                            change_summary=f"Issue #{num} state changed ({prev_state} -> {state})",
                            old_value={"state": prev_state},
                            new_value={"state": state},
                            detected_at=now,
                            source=source,
                        ))
                        detected_events.append(DigitalTwinEvent(
                            digital_twin_id=twin.id,
                            event_type=ev_type,
                            entity_type="issue",
                            entity_id=str(num),
                            title=f"Issue #{num} {state.capitalize()}: {title}",
                            description=f"Status transition from {prev_state} to {state}",
                            timestamp=parse_iso_datetime(iss.get("closed_at")) or now,
                            actor_login=user_login,
                            actor_avatar_url=user_avatar,
                            source=source,
                            event_metadata={"number": num, "state": state},
                        ))
            if new_issue_count > 0:
                summary_messages.append(f"{new_issue_count} new issue(s)")
            if closed_issue_count > 0:
                summary_messages.append(f"{closed_issue_count} issue(s) closed")

            # C. Pull Requests
            new_pr_count = 0
            merged_pr_count = 0
            for pr in raw_prs:
                num = pr.get("number", 0)
                state = pr.get("state", "open")
                is_merged = pr.get("merged_at") is not None
                title = pr.get("title", "")[:120]
                pr_user = (pr.get("user") or {}).get("login")
                pr_avatar = (pr.get("user") or {}).get("avatar_url")
                if num not in existing_prs:
                    new_pr_count += 1
                    detected_changes.append(DigitalTwinChange(
                        digital_twin_id=twin.id,
                        entity_type="pull_request",
                        entity_id=str(num),
                        change_type="CREATED",
                        change_summary=f"New PR #{num}: {title}",
                        new_value={"number": num, "title": title, "state": state, "is_merged": is_merged},
                        detected_at=now,
                        source=source,
                    ))
                    detected_events.append(DigitalTwinEvent(
                        digital_twin_id=twin.id,
                        event_type="PR_OPENED",
                        entity_type="pull_request",
                        entity_id=str(num),
                        title=f"PR #{num} Opened: {title}",
                        description=f"Pull request opened by {pr_user}",
                        timestamp=parse_iso_datetime(pr.get("created_at")) or now,
                        actor_login=pr_user,
                        actor_avatar_url=pr_avatar,
                        source=source,
                        event_metadata={"number": num, "html_url": pr.get("html_url")},
                    ))
                else:
                    prev_pr = existing_prs[num]
                    if not prev_pr.is_merged and is_merged:
                        merged_pr_count += 1
                        detected_changes.append(DigitalTwinChange(
                            digital_twin_id=twin.id,
                            entity_type="pull_request",
                            entity_id=str(num),
                            change_type="STATE_CHANGED",
                            change_summary=f"PR #{num} merged: {title}",
                            old_value={"state": prev_pr.state, "is_merged": False},
                            new_value={"state": state, "is_merged": True},
                            detected_at=now,
                            source=source,
                        ))
                        detected_events.append(DigitalTwinEvent(
                            digital_twin_id=twin.id,
                            event_type="PR_MERGED",
                            entity_type="pull_request",
                            entity_id=str(num),
                            title=f"PR #{num} Merged: {title}",
                            description=f"Merged into {project.default_branch}",
                            timestamp=parse_iso_datetime(pr.get("merged_at")) or now,
                            actor_login=pr_user,
                            actor_avatar_url=pr_avatar,
                            source=source,
                            event_metadata={"number": num, "merged": True},
                        ))
            if new_pr_count > 0:
                summary_messages.append(f"{new_pr_count} new PR(s)")
            if merged_pr_count > 0:
                summary_messages.append(f"{merged_pr_count} PR(s) merged")

            # D. Contributors
            new_contrib_count = 0
            for c in raw_contribs:
                login = c.get("login", "unknown")
                contributions = c.get("contributions", 0)
                if login not in existing_contribs:
                    new_contrib_count += 1
                    detected_changes.append(DigitalTwinChange(
                        digital_twin_id=twin.id,
                        entity_type="contributor",
                        entity_id=login,
                        change_type="CREATED",
                        change_summary=f"New contributor joined: {login}",
                        new_value={"login": login, "contributions": contributions},
                        detected_at=now,
                        source=source,
                    ))
                    detected_events.append(DigitalTwinEvent(
                        digital_twin_id=twin.id,
                        event_type="CONTRIBUTOR_ADDED",
                        entity_type="contributor",
                        entity_id=login,
                        title=f"New Contributor: {login}",
                        description=f"Recorded with {contributions} contributions",
                        timestamp=now,
                        actor_login=login,
                        actor_avatar_url=c.get("avatar_url"),
                        source=source,
                    ))
            if new_contrib_count > 0:
                summary_messages.append(f"{new_contrib_count} new contributor(s)")

            # E. Branches
            incoming_branch_names = set()
            new_branch_count = 0
            for b in raw_branches:
                b_name = b.get("name", "")
                if b_name:
                    incoming_branch_names.add(b_name)
                    if b_name not in existing_branches:
                        new_branch_count += 1
                        detected_changes.append(DigitalTwinChange(
                            digital_twin_id=twin.id,
                            entity_type="branch",
                            entity_id=b_name,
                            change_type="CREATED",
                            change_summary=f"New branch created: {b_name}",
                            new_value={"name": b_name, "commit_sha": (b.get("commit") or {}).get("sha")},
                            detected_at=now,
                            source=source,
                        ))
                        detected_events.append(DigitalTwinEvent(
                            digital_twin_id=twin.id,
                            event_type="BRANCH_CREATED",
                            entity_type="branch",
                            entity_id=b_name,
                            title=f"Branch Created: {b_name}",
                            description=f"New branch in repository {owner}/{repo}",
                            timestamp=now,
                            source=source,
                        ))
            # Deleted branches
            deleted_branch_count = 0
            if len(existing_branches) > 0 and len(incoming_branch_names) > 0:
                for b_name in existing_branches:
                    if b_name not in incoming_branch_names:
                        deleted_branch_count += 1
                        detected_changes.append(DigitalTwinChange(
                            digital_twin_id=twin.id,
                            entity_type="branch",
                            entity_id=b_name,
                            change_type="DELETED",
                            change_summary=f"Branch deleted: {b_name}",
                            old_value={"name": b_name},
                            detected_at=now,
                            source=source,
                        ))
                        detected_events.append(DigitalTwinEvent(
                            digital_twin_id=twin.id,
                            event_type="BRANCH_DELETED",
                            entity_type="branch",
                            entity_id=b_name,
                            title=f"Branch Removed: {b_name}",
                            description=f"Branch {b_name} no longer present in repository",
                            timestamp=now,
                            source=source,
                        ))
            if new_branch_count > 0:
                summary_messages.append(f"{new_branch_count} branch(es) created")
            if deleted_branch_count > 0:
                summary_messages.append(f"{deleted_branch_count} branch(es) removed")

            # F. Releases
            new_release_count = 0
            for r in raw_releases:
                tag = r.get("tag_name", "")
                if tag and tag not in existing_releases:
                    new_release_count += 1
                    rel_name = r.get("name") or tag
                    rel_author = (r.get("author") or {}).get("login")
                    detected_changes.append(DigitalTwinChange(
                        digital_twin_id=twin.id,
                        entity_type="release",
                        entity_id=tag,
                        change_type="CREATED",
                        change_summary=f"New release published: {tag} ({rel_name})",
                        new_value={"tag": tag, "name": rel_name},
                        detected_at=now,
                        source=source,
                    ))
                    detected_events.append(DigitalTwinEvent(
                        digital_twin_id=twin.id,
                        event_type="RELEASE_PUBLISHED",
                        entity_type="release",
                        entity_id=tag,
                        title=f"Release {tag}: {rel_name}",
                        description=f"Published release {tag}",
                        timestamp=parse_iso_datetime(r.get("published_at")) or now,
                        actor_login=rel_author,
                        actor_avatar_url=(r.get("author") or {}).get("avatar_url"),
                        source=source,
                    ))
            if new_release_count > 0:
                summary_messages.append(f"{new_release_count} new release(s)")

            # G. Repository files / tree
            new_file_count = 0
            for item in raw_tree[:500]:  # index up to 500 files for high responsiveness
                path = item.get("path")
                sha = item.get("sha")
                if path:
                    if path not in existing_files:
                        new_file_count += 1
                        detected_changes.append(DigitalTwinChange(
                            digital_twin_id=twin.id,
                            entity_type="file",
                            entity_id=path,
                            change_type="CREATED",
                            change_summary=f"File added: {path}",
                            new_value={"path": path, "sha": sha},
                            detected_at=now,
                            source=source,
                        ))
                    elif existing_files[path].sha != sha:
                        detected_changes.append(DigitalTwinChange(
                            digital_twin_id=twin.id,
                            entity_type="file",
                            entity_id=path,
                            change_type="UPDATED",
                            change_summary=f"File updated: {path}",
                            old_value={"sha": existing_files[path].sha},
                            new_value={"sha": sha},
                            detected_at=now,
                            source=source,
                        ))
            if new_file_count > 0:
                summary_messages.append(f"{new_file_count} new file(s) tracked")

            # H. Repository metadata changes (stars, description, default_branch)
            meta_changes = []
            if project.stars_count != meta.get("stargazers_count", project.stars_count):
                meta_changes.append(f"stars: {project.stars_count} -> {meta.get('stargazers_count', 0)}")
            if project.default_branch != default_branch:
                meta_changes.append(f"default branch: {project.default_branch} -> {default_branch}")
            if project.description != meta.get("description"):
                meta_changes.append("description updated")

            if meta_changes:
                detected_changes.append(DigitalTwinChange(
                    digital_twin_id=twin.id,
                    entity_type="repository",
                    entity_id=project.full_name,
                    change_type="UPDATED",
                    change_summary=f"Repository metadata updated ({', '.join(meta_changes)})",
                    detected_at=now,
                    source=source,
                ))
                detected_events.append(DigitalTwinEvent(
                    digital_twin_id=twin.id,
                    event_type="REPOSITORY_UPDATED",
                    entity_type="repository",
                    entity_id=project.full_name,
                    title=f"Repository Updated: {project.full_name}",
                    description=', '.join(meta_changes),
                    timestamp=now,
                    source=source,
                ))
                summary_messages.append("Repository metadata updated")

        # 3. IDEMPOTENCY CHECK (For non-initial syncs)
        if not is_initial and len(detected_changes) == 0:
            twin.last_synced_at = now
            twin.status = "ACTIVE"
            twin.error_message = None
            project.last_synced_at = now
            project.status = "synced"
            db.commit()
            db.refresh(twin)
            try:
                from app.services.health.health_service import health_service
                from app.services.risk.risk_service import risk_service
                health_service.calculate_and_persist_health(project.id, db, twin_version=twin.current_version)
                risk_service.evaluate_and_persist_risks(project.id, db)
            except Exception as e:
                logger.error(f"Error updating health/risks on idempotent sync for project {project.id}: {str(e)}", exc_info=True)
            logger.info(f"Sync complete for {project.full_name}: No changes detected. Idempotent version kept at v{twin.current_version}.")
            return {
                "twin_id": twin.id,
                "project_id": project.id,
                "previous_version": twin.current_version,
                "current_version": twin.current_version,
                "status": "ACTIVE",
                "changes_detected": 0,
                "changes_summary": ["No repository changes detected."],
                "message": "No repository changes detected. Digital Twin state is current.",
                "synced_at": now,
            }

        # 4. PERSIST UPDATED ENTITIES INTO DATABASE
        # Project Metadata
        project.name = meta.get("name", repo)
        project.description = meta.get("description")
        project.html_url = meta.get("html_url", project.html_url)
        project.default_branch = default_branch
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

        # Commits
        db.query(Commit).filter(Commit.project_id == project.id).delete()
        for cm in raw_commits:
            commit_info = cm.get("commit", {})
            author_info = commit_info.get("author", {})
            gh_author = cm.get("author") or {}
            db.add(Commit(
                project_id=project.id,
                sha=cm.get("sha", "")[:40],
                message=commit_info.get("message", "").split("\n")[0][:500],
                author_name=author_info.get("name"),
                author_email=author_info.get("email"),
                author_date=parse_iso_datetime(author_info.get("date")),
                author_login=gh_author.get("login"),
                author_avatar_url=gh_author.get("avatar_url"),
                html_url=cm.get("html_url"),
            ))

        # Contributors
        db.query(Contributor).filter(Contributor.project_id == project.id).delete()
        for c in raw_contribs:
            db.add(Contributor(
                project_id=project.id,
                github_id=c.get("id"),
                login=c.get("login", "unknown"),
                avatar_url=c.get("avatar_url"),
                html_url=c.get("html_url"),
                contributions=c.get("contributions", 0),
                contributor_type=c.get("type", "User"),
            ))

        # Issues
        db.query(Issue).filter(Issue.project_id == project.id).delete()
        for iss in raw_issues:
            iss_user = iss.get("user") or {}
            labels = [l.get("name") for l in iss.get("labels", []) if isinstance(l, dict)]
            db.add(Issue(
                project_id=project.id,
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
                html_url=iss.get("html_url"),
            ))

        # Pull Requests
        db.query(PullRequest).filter(PullRequest.project_id == project.id).delete()
        open_pr_count = 0
        for pr in raw_prs:
            if pr.get("state") == "open":
                open_pr_count += 1
            pr_user = pr.get("user") or {}
            db.add(PullRequest(
                project_id=project.id,
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
                html_url=pr.get("html_url"),
            ))
        project.open_prs_count = open_pr_count

        # Releases
        db.query(Release).filter(Release.project_id == project.id).delete()
        for rel in raw_releases:
            rel_author = rel.get("author") or {}
            db.add(Release(
                project_id=project.id,
                github_id=rel.get("id"),
                tag_name=rel.get("tag_name", "v0.0.0"),
                name=rel.get("name") or rel.get("tag_name"),
                author_login=rel_author.get("login"),
                published_at=parse_iso_datetime(rel.get("published_at")),
                html_url=rel.get("html_url"),
                is_prerelease=rel.get("prerelease", False),
            ))

        # Branches
        db.query(Branch).filter(Branch.project_id == project.id).delete()
        for br in raw_branches:
            commit_info = br.get("commit") or {}
            db.add(Branch(
                project_id=project.id,
                name=br.get("name", "main"),
                commit_sha=commit_info.get("sha"),
                is_protected=br.get("protected", False),
                is_default=(br.get("name") == project.default_branch),
            ))

        # Files / Tree
        if raw_tree:
            db.query(RepositoryFile).filter(RepositoryFile.project_id == project.id).delete()
            for item in raw_tree[:500]:
                f_path = item.get("path", "")
                f_type = item.get("type", "blob")
                parts = f_path.rsplit("/", 1)
                directory = parts[0] if len(parts) > 1 else ""
                filename = parts[-1]
                ext = f".{filename.rsplit('.', 1)[-1]}" if "." in filename else ""
                db.add(RepositoryFile(
                    project_id=project.id,
                    path=f_path,
                    filename=filename,
                    extension=ext,
                    directory=directory,
                    size=item.get("size", 0) or 0,
                    file_type=f_type,
                    sha=item.get("sha"),
                    first_seen=now,
                    last_seen=now,
                ))

        # Calculate Repository Health Index
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
        project.last_synced_at = now
        project.status = "synced"

        # 5. INCREMENT TWIN VERSION & CREATE SNAPSHOT
        previous_version = twin.current_version
        if is_initial:
            new_version = 1
        else:
            new_version = previous_version + 1

        twin.current_version = new_version
        twin.last_synced_at = now
        twin.status = "ACTIVE"
        twin.error_message = None

        entity_counts = {
            "commits": len(raw_commits),
            "contributors": len(raw_contribs),
            "issues": len(raw_issues),
            "pull_requests": len(raw_prs),
            "branches": len(raw_branches),
            "releases": len(raw_releases),
            "files": len(raw_tree[:500]) if raw_tree else 0,
        }

        fidelity_score, _ = self._compute_fidelity_score(entity_counts)
        twin.fidelity_score = fidelity_score

        # State data representation
        state_data = {
            "default_branch": default_branch,
            "latest_commit_sha": raw_commits[0].get("sha") if raw_commits else None,
            "latest_release_tag": raw_releases[0].get("tag_name") if raw_releases else None,
            "open_issues_count": project.open_issues_count,
            "open_prs_count": project.open_prs_count,
            "stars_count": project.stars_count,
            "forks_count": project.forks_count,
            "primary_language": project.language,
            "health_score": project.health_score,
            "fidelity_score": fidelity_score,
        }

        snapshot_summary = "Initial sync" if is_initial else f"{len(detected_changes)} change(s): {', '.join(summary_messages[:3])}"

        snapshot = DigitalTwinSnapshot(
            digital_twin_id=twin.id,
            version=new_version,
            source=source,
            summary=snapshot_summary,
            change_count=len(detected_changes),
            entity_counts=entity_counts,
            state_data=state_data,
        )
        db.add(snapshot)
        db.flush()  # obtain snapshot.id

        # Attach snapshot_id to detected changes and events
        for chg in detected_changes:
            chg.snapshot_id = snapshot.id
            db.add(chg)

        for ev in detected_events:
            ev.snapshot_id = snapshot.id
            db.add(ev)

        # Emit TWIN_SYNCHRONIZED event
        db.add(DigitalTwinEvent(
            digital_twin_id=twin.id,
            snapshot_id=snapshot.id,
            event_type="TWIN_SYNCHRONIZED",
            entity_type="twin",
            entity_id=str(twin.id),
            title=f"Digital Twin Synchronized: v{previous_version} → v{new_version}",
            description=f"Snapshot v{new_version} recorded with {len(detected_changes)} detected changes.",
            timestamp=now,
            source=source,
            event_metadata={
                "version_from": previous_version,
                "version_to": new_version,
                "change_count": len(detected_changes),
            }
        ))

        db.commit()
        db.refresh(twin)
        db.refresh(snapshot)

        # Trigger Phase 4 Software Health & Risk Evaluation
        try:
            from app.services.health.health_service import health_service
            from app.services.risk.risk_service import risk_service
            health_service.calculate_and_persist_health(project.id, db, twin_version=new_version)
            risk_service.evaluate_and_persist_risks(project.id, db)
        except Exception as e:
            logger.error(f"Error calculating health/risks post-sync for project {project.id}: {str(e)}", exc_info=True)

        return {
            "twin_id": twin.id,
            "project_id": project.id,
            "previous_version": previous_version,
            "current_version": new_version,
            "status": "ACTIVE",
            "changes_detected": len(detected_changes),
            "changes_summary": summary_messages or ["Repository state synchronized."],
            "message": f"Digital Twin synchronized: v{previous_version} → v{new_version}. {len(detected_changes)} changes detected.",
            "synced_at": now,
        }

    def get_current_state(self, project_id: int, db: Session) -> Dict[str, Any]:
        """
        Retrieves the complete current Digital Twin state for a project.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        twin = self.get_or_create_twin(project_id, db)
        twin_data = self.get_twin_response_data(twin)

        # Entity counts from database
        commit_count = db.query(Commit).filter(Commit.project_id == project_id).count()
        contributor_count = db.query(Contributor).filter(Contributor.project_id == project_id).count()
        issue_count = db.query(Issue).filter(Issue.project_id == project_id).count()
        pr_count = db.query(PullRequest).filter(PullRequest.project_id == project_id).count()
        branch_count = db.query(Branch).filter(Branch.project_id == project_id).count()
        release_count = db.query(Release).filter(Release.project_id == project_id).count()
        file_count = db.query(RepositoryFile).filter(RepositoryFile.project_id == project_id).count()

        entity_counts = {
            "commits": commit_count,
            "contributors": contributor_count,
            "issues": issue_count,
            "pull_requests": pr_count,
            "branches": branch_count,
            "releases": release_count,
            "files": file_count,
        }

        fidelity_score, fidelity_components = self._compute_fidelity_score(entity_counts)

        # Latest snapshot
        latest_snapshot = (
            db.query(DigitalTwinSnapshot)
            .filter(DigitalTwinSnapshot.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinSnapshot.version))
            .first()
        )

        # Latest commit & release
        latest_commit_obj = (
            db.query(Commit)
            .filter(Commit.project_id == project_id)
            .order_by(desc(Commit.author_date))
            .first()
        )
        latest_release_obj = (
            db.query(Release)
            .filter(Release.project_id == project_id)
            .order_by(desc(Release.published_at))
            .first()
        )

        latest_commit = {
            "sha": latest_commit_obj.sha,
            "message": latest_commit_obj.message,
            "author": latest_commit_obj.author_name or latest_commit_obj.author_login,
            "date": latest_commit_obj.author_date.isoformat() if latest_commit_obj.author_date else None,
        } if latest_commit_obj else None

        latest_release = {
            "tag": latest_release_obj.tag_name,
            "name": latest_release_obj.name,
            "published_at": latest_release_obj.published_at.isoformat() if latest_release_obj.published_at else None,
        } if latest_release_obj else None

        # Recent changes and events
        recent_changes = (
            db.query(DigitalTwinChange)
            .filter(DigitalTwinChange.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinChange.detected_at))
            .limit(20)
            .all()
        )

        recent_events = (
            db.query(DigitalTwinEvent)
            .filter(DigitalTwinEvent.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinEvent.timestamp))
            .limit(25)
            .all()
        )

        return {
            "twin": twin_data,
            "repository": {
                "id": project.id,
                "owner": project.github_owner,
                "repo": project.github_repo,
                "full_name": project.full_name,
                "html_url": project.html_url,
                "description": project.description,
                "default_branch": project.default_branch,
                "language": project.language,
                "stars": project.stars_count,
                "forks": project.forks_count,
                "open_issues": project.open_issues_count,
                "open_prs": project.open_prs_count,
                "license": project.license_name,
                "health_score": project.health_score,
            },
            "current_snapshot": latest_snapshot,
            "entity_counts": entity_counts,
            "latest_commit": latest_commit,
            "latest_release": latest_release,
            "current_branch": project.default_branch,
            "fidelity_components": fidelity_components,
            "recent_changes": recent_changes,
            "recent_events": recent_events,
        }

    def get_snapshots(self, project_id: int, db: Session) -> List[DigitalTwinSnapshot]:
        """Returns all snapshots for a project ordered by version descending."""
        twin = self.get_or_create_twin(project_id, db)
        return (
            db.query(DigitalTwinSnapshot)
            .filter(DigitalTwinSnapshot.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinSnapshot.version))
            .all()
        )

    def get_snapshot_detail(self, project_id: int, snapshot_id: int, db: Session) -> Dict[str, Any]:
        """Returns detailed snapshot data including its associated change set."""
        twin = self.get_or_create_twin(project_id, db)
        snapshot = (
            db.query(DigitalTwinSnapshot)
            .filter(DigitalTwinSnapshot.id == snapshot_id, DigitalTwinSnapshot.digital_twin_id == twin.id)
            .first()
        )
        if not snapshot:
            raise ValueError(f"Snapshot with ID {snapshot_id} not found for project {project_id}.")

        changes = (
            db.query(DigitalTwinChange)
            .filter(DigitalTwinChange.snapshot_id == snapshot.id)
            .order_by(desc(DigitalTwinChange.detected_at))
            .all()
        )

        return {
            "snapshot": snapshot,
            "changes": changes,
        }

    def compare_snapshots(
        self,
        project_id: int,
        v_from: Optional[int],
        v_to: Optional[int],
        db: Session,
    ) -> Dict[str, Any]:
        """
        Compares two snapshot versions (e.g. v1 vs v2). If not specified,
        defaults to comparing the latest version against its predecessor.
        """
        twin = self.get_or_create_twin(project_id, db)
        all_snapshots = (
            db.query(DigitalTwinSnapshot)
            .filter(DigitalTwinSnapshot.digital_twin_id == twin.id)
            .order_by(DigitalTwinSnapshot.version.asc())
            .all()
        )

        if not all_snapshots:
            return {
                "project_id": project_id,
                "twin_id": twin.id,
                "v_from": 0,
                "v_to": 0,
                "added": [],
                "updated": [],
                "removed": [],
                "summary": {"message": "No snapshots recorded yet."},
            }

        # Resolve versions
        if v_to is None:
            v_to = all_snapshots[-1].version
        if v_from is None:
            v_from = all_snapshots[-2].version if len(all_snapshots) > 1 else all_snapshots[0].version

        s_from = next((s for s in all_snapshots if s.version == v_from), None)
        s_to = next((s for s in all_snapshots if s.version == v_to), None)

        if not s_from or not s_to:
            raise ValueError(f"Invalid versions requested for comparison: v{v_from} and v{v_to}.")

        # Retrieve changes in snapshots between (v_from, v_to]
        target_snapshots = [s.id for s in all_snapshots if v_from < s.version <= v_to]
        changes_between: List[DigitalTwinChange] = []
        if target_snapshots:
            changes_between = (
                db.query(DigitalTwinChange)
                .filter(DigitalTwinChange.snapshot_id.in_(target_snapshots))
                .order_by(DigitalTwinChange.detected_at.desc())
                .all()
            )

        added = []
        updated = []
        removed = []

        for chg in changes_between:
            item = {
                "entity_type": chg.entity_type,
                "entity_id": chg.entity_id,
                "change_type": chg.change_type.lower(),
                "summary": chg.change_summary,
                "old_value": chg.old_value,
                "new_value": chg.new_value,
            }
            if chg.change_type == "CREATED":
                added.append(item)
            elif chg.change_type in ("UPDATED", "STATE_CHANGED"):
                updated.append(item)
            elif chg.change_type == "DELETED":
                removed.append(item)

        counts_from = s_from.entity_counts or {}
        counts_to = s_to.entity_counts or {}
        diff_counts = {}
        for k in set(list(counts_from.keys()) + list(counts_to.keys())):
            diff_counts[k] = counts_to.get(k, 0) - counts_from.get(k, 0)

        return {
            "project_id": project_id,
            "twin_id": twin.id,
            "v_from": v_from,
            "v_to": v_to,
            "added": added,
            "updated": updated,
            "removed": removed,
            "summary": {
                "total_added": len(added),
                "total_updated": len(updated),
                "total_removed": len(removed),
                "entity_count_diffs": diff_counts,
                "version_span": f"v{v_from} → v{v_to}",
            },
        }

    def get_changes(
        self,
        project_id: int,
        db: Session,
        limit: int = 50,
        snapshot_id: Optional[int] = None,
    ) -> List[DigitalTwinChange]:
        """Returns detected changes for a project, optionally filtered by snapshot."""
        twin = self.get_or_create_twin(project_id, db)
        query = db.query(DigitalTwinChange).filter(DigitalTwinChange.digital_twin_id == twin.id)
        if snapshot_id:
            query = query.filter(DigitalTwinChange.snapshot_id == snapshot_id)
        return query.order_by(desc(DigitalTwinChange.detected_at)).limit(limit).all()

    def get_events(self, project_id: int, db: Session, limit: int = 50) -> List[DigitalTwinEvent]:
        """Returns chronological event stream for a project's Digital Twin."""
        twin = self.get_or_create_twin(project_id, db)
        return (
            db.query(DigitalTwinEvent)
            .filter(DigitalTwinEvent.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinEvent.timestamp))
            .limit(limit)
            .all()
        )

    def get_entities_summary(self, project_id: int, db: Session) -> Dict[str, Any]:
        """Returns detailed breakdown of all entities tracked by this Digital Twin."""
        twin = self.get_or_create_twin(project_id, db)

        commit_count = db.query(Commit).filter(Commit.project_id == project_id).count()
        contributor_count = db.query(Contributor).filter(Contributor.project_id == project_id).count()
        issue_count = db.query(Issue).filter(Issue.project_id == project_id).count()
        pr_count = db.query(PullRequest).filter(PullRequest.project_id == project_id).count()
        branch_count = db.query(Branch).filter(Branch.project_id == project_id).count()
        release_count = db.query(Release).filter(Release.project_id == project_id).count()
        file_count = db.query(RepositoryFile).filter(RepositoryFile.project_id == project_id).count()

        counts = {
            "commits": commit_count,
            "contributors": contributor_count,
            "issues": issue_count,
            "pull_requests": pr_count,
            "branches": branch_count,
            "releases": release_count,
            "files": file_count,
        }
        total = sum(counts.values())

        breakdown = [
            {"entity": "Commits", "count": commit_count, "description": "Git commits in project history"},
            {"entity": "Contributors", "count": contributor_count, "description": "Active repository contributors"},
            {"entity": "Issues", "count": issue_count, "description": "Tracked GitHub issues"},
            {"entity": "Pull Requests", "count": pr_count, "description": "Open and merged pull requests"},
            {"entity": "Branches", "count": branch_count, "description": "Active repository branches"},
            {"entity": "Releases", "count": release_count, "description": "Published version milestones"},
            {"entity": "Files & Tree", "count": file_count, "description": "Indexed source and asset files"},
        ]

        return {
            "project_id": project_id,
            "twin_id": twin.id,
            "total_entities": total,
            "counts": counts,
            "breakdown": breakdown,
        }


digital_twin_service = DigitalTwinService()
