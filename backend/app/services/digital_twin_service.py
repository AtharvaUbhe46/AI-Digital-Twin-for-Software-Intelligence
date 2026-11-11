import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.core.config import settings
from app.core.datetime_utils import (
    utc_now,
    ensure_utc,
    parse_iso_datetime,
    safe_datetime_diff_minutes,
    format_iso_utc,
)
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
from app.services.sync_service import calculate_repository_health_index

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

    @classmethod
    def calculate_data_coverage(
        cls,
        entity_counts: Dict[str, int],
        category_status: Optional[Dict[str, str]] = None,
        is_initialized: bool = True,
    ) -> Tuple[Optional[float], List[Dict[str, Any]]]:
        """
        Evaluates Data Coverage based on real collection and validation results.
        Formula: Data Coverage = (Successfully collected and validated applicable categories / Total applicable categories) * 100
        Categories supported:
        1. metadata: Repository metadata & attributes
        2. commits: Git commit history
        3. contributors: Contributor roster
        4. issues: Issue tracking & state
        5. pull_requests: PR review pipeline
        6. branches: Active branches
        7. releases: Published milestones & tags
        8. files: Source tree and file nodes
        """
        if not is_initialized:
            return None, [
                {"key": k, "name": n, "synced": 0, "status": "NOT_COLLECTED", "active": False, "applicable": True}
                for k, n in [
                    ("metadata", "Repository Metadata"),
                    ("commits", "Commits"),
                    ("contributors", "Contributors"),
                    ("issues", "Issues"),
                    ("pull_requests", "Pull Requests"),
                    ("branches", "Branches"),
                    ("releases", "Releases"),
                    ("files", "Repository Files & Tree"),
                ]
            ]

        categories_def = [
            ("metadata", "Repository Metadata", "Repository description, default branch, language, and settings.", "settings"),
            ("commits", "Commits", "Git commit history and commit metadata.", "git-commit"),
            ("contributors", "Contributors", "Active developers and contribution counts.", "users"),
            ("issues", "Issues", "Issue tracking, labels, and state transitions.", "alert-circle"),
            ("pull_requests", "Pull Requests", "Code review pull requests and merge statuses.", "git-pull-request"),
            ("branches", "Branches", "Active and default branch references.", "git-branch"),
            ("releases", "Releases", "Published tags and release milestones.", "tag"),
            ("files", "Repository Files & Tree", "Indexed source files and directory nodes.", "folder-tree"),
        ]

        components = []
        valid_count = 0
        status_map = category_status or {}

        for key, label, description, icon in categories_def:
            count = entity_counts.get(key, 0)
            cat_stat = status_map.get(key)
            if not cat_stat:
                cat_stat = "COLLECTED" if count > 0 else "EMPTY"

            # Both COLLECTED (>0 items) and EMPTY (0 items verified cleanly) count as successfully collected and validated
            is_valid = cat_stat in ("COLLECTED", "EMPTY")
            if is_valid:
                valid_count += 1

            components.append({
                "key": key,
                "name": label,
                "description": description,
                "synced": count,
                "status": cat_stat,
                "icon": icon,
                "active": count > 0,
                "applicable": True,
                "validated": is_valid,
            })

        coverage_score = round((valid_count / len(categories_def)) * 100.0, 1)
        return coverage_score, components

    @classmethod
    def calculate_twin_health_score(
        cls,
        twin: DigitalTwin,
        data_coverage: Optional[float],
        snapshot_count: int,
        project: Optional[Project] = None,
        entity_counts: Optional[Dict[str, int]] = None,
    ) -> Tuple[Optional[float], Dict[str, Any]]:
        """
        Calculates deterministic Digital Twin Operational Health Score (0-100%).
        This measures the operational fidelity and synchronization reliability of the Digital Twin itself.
        Weights:
        - Synchronization Reliability: 25%
        - Data Freshness: 25%
        - Data Coverage: 25%
        - Snapshot Availability & History: 15%
        - Data Consistency & Integrity: 10%
        Total = 100%
        """
        if twin.status == "NOT_INITIALIZED" or not twin.last_synced_at:
            return None, {
                "score": None,
                "status": "UNAVAILABLE",
                "classification": "Unavailable",
                "formula": "Digital Twin Health Score = Sync Reliability (25%) + Data Freshness (25%) + Data Coverage (25%) + Snapshot Availability (15%) + Data Consistency (10%)",
                "explanation": "Digital Twin has not yet been initialized with synchronized repository data.",
                "components": [],
            }

        now = utc_now()
        last_synced = ensure_utc(twin.last_synced_at)
        staleness_minutes = safe_datetime_diff_minutes(now, last_synced) or 0.0

        # Pillar 1: Synchronization Reliability (25%)
        effective_status = twin.status
        if twin.status in ("ACTIVE", "SUCCESS"):
            c1_score = 25.0
            c1_detail = "Last synchronization completed without errors"
        elif twin.status == "PARTIAL_SUCCESS":
            c1_score = 15.0
            c1_detail = "Partial synchronization with non-fatal category warnings"
        elif twin.status == "OUTDATED":
            c1_score = 18.0
            c1_detail = "Prior sync succeeded; pending refresh"
        elif twin.status == "SYNCING":
            c1_score = 20.0
            c1_detail = "Synchronization currently in progress"
        elif twin.status in ("ERROR", "FAILED"):
            c1_score = 5.0
            c1_detail = f"Active sync failure: {twin.error_message or 'Unknown error'}"
        else:
            c1_score = 10.0
            c1_detail = f"Status: {twin.status}"

        # Pillar 2: Data Freshness (25%)
        threshold = twin.stale_threshold_minutes or 60
        if staleness_minutes <= threshold:
            c2_score = 25.0
            c2_detail = f"Synchronized {round(staleness_minutes)}m ago (within {threshold}m threshold)"
        elif staleness_minutes <= threshold * 4:
            c2_score = 20.0
            c2_detail = f"Synchronized {round(staleness_minutes / 60.0, 1)}h ago (recent)"
        elif staleness_minutes <= 1440:  # 24h
            c2_score = 15.0
            c2_detail = f"Synchronized {round(staleness_minutes / 60.0, 1)}h ago (acceptable)"
        elif staleness_minutes <= 10080:  # 7 days
            c2_score = 10.0
            c2_detail = f"Synchronized {round(staleness_minutes / 1440.0, 1)}d ago (aging)"
        else:
            c2_score = 3.0
            c2_detail = f"Synchronized over 7 days ago ({round(staleness_minutes / 1440.0, 1)}d)"

        # Pillar 3: Data Coverage (25%)
        cov = data_coverage if data_coverage is not None else 0.0
        c3_score = round((cov / 100.0) * 25.0, 1)
        c3_detail = f"{cov}% applicable categories collected and validated"

        # Pillar 4: Snapshot Availability & History (15%)
        if snapshot_count >= 3:
            c4_score = 15.0
            c4_detail = f"{snapshot_count} snapshots recorded (established historical ledger)"
        elif snapshot_count == 2:
            c4_score = 12.0
            c4_detail = "2 snapshots recorded (version comparison enabled)"
        elif snapshot_count == 1:
            c4_score = 8.0
            c4_detail = "1 snapshot recorded (baseline checkpoint established)"
        else:
            c4_score = 0.0
            c4_detail = "No historical snapshots available"

        # Pillar 5: Data Consistency & Integrity (10%)
        c5_score = 0.0
        checks_passed = []
        if project and project.default_branch:
            c5_score += 3.0
            checks_passed.append("default branch verified")
        if project and project.full_name:
            c5_score += 2.5
            checks_passed.append("repository metadata verified")
        counts = entity_counts or {}
        if counts.get("commits", 0) > 0 or (project and project.status == "synced"):
            c5_score += 2.5
            checks_passed.append("entity linkage intact")
        if all(v >= 0 for v in counts.values()):
            c5_score += 2.0
            checks_passed.append("record counters coherent")

        c5_detail = f"{', '.join(checks_passed)}" if checks_passed else "Basic schema validation"

        total_score = round(min(100.0, max(0.0, c1_score + c2_score + c3_score + c4_score + c5_score)), 1)

        # Classifications
        if total_score >= 85:
            classification = "Optimal"
        elif total_score >= 70:
            classification = "Healthy"
        elif total_score >= 50:
            classification = "Degraded"
        elif total_score >= 30:
            classification = "At Risk"
        else:
            classification = "Critical"

        components = [
            {
                "name": "Synchronization Reliability",
                "weight": "25%",
                "score": round(c1_score, 1),
                "max_score": 25.0,
                "detail": c1_detail,
            },
            {
                "name": "Data Freshness",
                "weight": "25%",
                "score": round(c2_score, 1),
                "max_score": 25.0,
                "detail": c2_detail,
            },
            {
                "name": "Data Coverage",
                "weight": "25%",
                "score": round(c3_score, 1),
                "max_score": 25.0,
                "detail": c3_detail,
            },
            {
                "name": "Snapshot Availability & History",
                "weight": "15%",
                "score": round(c4_score, 1),
                "max_score": 15.0,
                "detail": c4_detail,
            },
            {
                "name": "Data Consistency & Integrity",
                "weight": "10%",
                "score": round(c5_score, 1),
                "max_score": 10.0,
                "detail": c5_detail,
            },
        ]

        details = {
            "score": total_score,
            "status": classification,
            "classification": classification,
            "formula": "Digital Twin Health Score = Sync Reliability (25%) + Data Freshness (25%) + Data Coverage (25%) + Snapshot Availability (15%) + Data Consistency (10%)",
            "explanation": "Calculates operational health and synchronization reliability of the Digital Twin based on measured synchronization status, data freshness, coverage completeness, snapshot ledger depth, and structural integrity.",
            "components": components,
        }

        return total_score, details

    @classmethod
    def get_twin_response_data(cls, twin: DigitalTwin, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Augments DigitalTwin model with dynamic staleness, computed status,
        real Data Coverage, and transparent Digital Twin Health Score.
        """
        now = utc_now()
        staleness_minutes: Optional[float] = None
        is_outdated = False
        effective_status = twin.status

        if twin.last_synced_at:
            last_synced = ensure_utc(twin.last_synced_at)
            staleness_minutes = safe_datetime_diff_minutes(now, last_synced)
            if staleness_minutes is not None and staleness_minutes > twin.stale_threshold_minutes:
                is_outdated = True
                if twin.status in ("ACTIVE", "SUCCESS"):
                    effective_status = "OUTDATED"

        # Map internal status to documented states:
        # IDLE, SYNCING, ACTIVE (SUCCESS), OUTDATED, PARTIAL_SUCCESS, FAILED, NOT_INITIALIZED
        if effective_status == "ERROR":
            effective_status = "FAILED"

        # Calculate coverage & health if db session provided
        data_coverage = None
        coverage_details = None
        health_score = None
        health_details = None

        if db:
            project_id = twin.project_id
            commit_count = db.query(Commit).filter(Commit.project_id == project_id).count()
            contributor_count = db.query(Contributor).filter(Contributor.project_id == project_id).count()
            issue_count = db.query(Issue).filter(Issue.project_id == project_id).count()
            pr_count = db.query(PullRequest).filter(PullRequest.project_id == project_id).count()
            branch_count = db.query(Branch).filter(Branch.project_id == project_id).count()
            release_count = db.query(Release).filter(Release.project_id == project_id).count()
            file_count = db.query(RepositoryFile).filter(RepositoryFile.project_id == project_id).count()

            entity_counts = {
                "metadata": 1 if twin.status != "NOT_INITIALIZED" else 0,
                "commits": commit_count,
                "contributors": contributor_count,
                "issues": issue_count,
                "pull_requests": pr_count,
                "branches": branch_count,
                "releases": release_count,
                "files": file_count,
            }

            data_coverage, coverage_components = cls.calculate_data_coverage(
                entity_counts,
                is_initialized=(twin.status != "NOT_INITIALIZED")
            )
            coverage_details = {
                "coverage_score": data_coverage,
                "components": coverage_components,
                "formula": "Data Coverage = (Successfully collected & validated applicable categories / Total applicable categories) * 100",
            }

            snapshot_count = db.query(DigitalTwinSnapshot).filter(DigitalTwinSnapshot.digital_twin_id == twin.id).count()
            project = db.query(Project).filter(Project.id == project_id).first()
            health_score, health_details = cls.calculate_twin_health_score(
                twin=twin,
                data_coverage=data_coverage,
                snapshot_count=snapshot_count,
                project=project,
                entity_counts=entity_counts,
            )

        return {
            "id": twin.id,
            "project_id": twin.project_id,
            "current_version": twin.current_version,
            "status": effective_status,
            "error_message": twin.error_message,
            "last_synced_at": ensure_utc(twin.last_synced_at),
            "fidelity_score": data_coverage if data_coverage is not None else twin.fidelity_score,
            "data_coverage": data_coverage,
            "data_coverage_details": coverage_details,
            "health_score": health_score,
            "health_details": health_details,
            "stale_threshold_minutes": twin.stale_threshold_minutes,
            "is_outdated": is_outdated,
            "staleness_minutes": staleness_minutes,
            "created_at": ensure_utc(twin.created_at),
            "updated_at": ensure_utc(twin.updated_at),
        }

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

        twin.status = "SYNCING"
        twin.error_message = None
        db.commit()

        try:
            return await self._execute_sync(project=project, twin=twin, db=db, is_initial=True, source="initial_sync")
        except Exception as exc:
            db.rollback()
            twin.status = "ERROR"
            twin.error_message = str(exc)
            try:
                db.commit()
            except Exception:
                pass
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
            try:
                db.commit()
            except Exception:
                pass
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
        Internal synchronization routine with full Change Detection, State Versioning,
        and Robust Failure Handling.
        """
        owner = project.github_owner
        repo = project.github_repo
        now = utc_now()
        logger.info(f"Executing Digital Twin sync for {owner}/{repo} (is_initial={is_initial})...")

        # 1. Existing entities in database for change detection and deduplication
        existing_commits = {c.sha: c for c in db.query(Commit).filter(Commit.project_id == project.id).all()}
        existing_contribs = {c.login: c for c in db.query(Contributor).filter(Contributor.project_id == project.id).all()}
        existing_issues = {i.number: i for i in db.query(Issue).filter(Issue.project_id == project.id).all()}
        existing_prs = {p.number: p for p in db.query(PullRequest).filter(PullRequest.project_id == project.id).all()}
        existing_branches = {b.name: b for b in db.query(Branch).filter(Branch.project_id == project.id).all()}
        existing_releases = {r.tag_name: r for r in db.query(Release).filter(Release.project_id == project.id).all()}
        existing_files = {f.path: f for f in db.query(RepositoryFile).filter(RepositoryFile.project_id == project.id).all()}

        default_branch = project.default_branch or "main"
        category_status: Dict[str, str] = {}

        # 2. Fetch live GitHub data
        if is_initial and len(existing_commits) > 0:
            logger.info(f"Reusing freshly synchronized repository entities from DB for twin v1 of {owner}/{repo}")
            meta = {
                "name": project.name,
                "description": project.description,
                "html_url": project.html_url,
                "default_branch": default_branch,
                "language": project.language,
                "visibility": project.visibility,
                "stargazers_count": project.stars_count,
                "forks_count": project.forks_count,
                "subscribers_count": project.watchers_count,
                "open_issues_count": project.open_issues_count,
                "created_at": format_iso_utc(project.repo_created_at),
                "updated_at": format_iso_utc(project.repo_updated_at),
                "pushed_at": format_iso_utc(project.repo_pushed_at),
            }
            raw_commits = [{"sha": c.sha, "commit": {"message": c.message, "author": {"name": c.author_name, "date": format_iso_utc(c.author_date)}}, "author": {"login": c.author_login, "avatar_url": c.author_avatar_url}, "html_url": c.html_url} for c in existing_commits.values()]
            raw_contribs = [{"id": c.github_id, "login": c.login, "avatar_url": c.avatar_url, "html_url": c.html_url, "contributions": c.contributions, "type": c.contributor_type} for c in existing_contribs.values()]
            raw_issues = [{"id": i.github_id, "number": i.number, "title": i.title, "state": i.state, "user": {"login": i.author_login, "avatar_url": i.author_avatar_url}, "created_at": format_iso_utc(i.created_at), "closed_at": format_iso_utc(i.closed_at), "html_url": i.html_url, "comments": i.comments_count} for i in existing_issues.values()]
            raw_prs = [{"id": p.github_id, "number": p.number, "title": p.title, "state": p.state, "user": {"login": p.author_login, "avatar_url": p.author_avatar_url}, "merged_at": format_iso_utc(p.merged_at), "created_at": format_iso_utc(p.created_at), "updated_at": format_iso_utc(p.updated_at), "closed_at": format_iso_utc(p.closed_at), "draft": p.draft, "html_url": p.html_url} for p in existing_prs.values()]
            raw_releases = [{"id": r.github_id, "tag_name": r.tag_name, "name": r.name, "author": {"login": r.author_login}, "published_at": format_iso_utc(r.published_at), "html_url": r.html_url, "prerelease": r.is_prerelease} for r in existing_releases.values()]
            raw_branches = [{"name": b.name, "commit": {"sha": b.commit_sha}, "protected": b.is_protected} for b in existing_branches.values()]
            try:
                raw_tree = await github_service.get_repo_tree(owner, repo, tree_sha=default_branch)
                category_status["files"] = "COLLECTED" if raw_tree else "EMPTY"
            except Exception:
                raw_tree = []
                category_status["files"] = "FAILED"

            for k, items in [("metadata", [1]), ("commits", raw_commits), ("contributors", raw_contribs), ("issues", raw_issues), ("pull_requests", raw_prs), ("releases", raw_releases), ("branches", raw_branches)]:
                category_status[k] = "COLLECTED" if items else "EMPTY"

        else:
            # Concurrently fetch from GitHub
            (
                meta_res,
                commits_res,
                contribs_res,
                issues_res,
                prs_res,
                releases_res,
                branches_res,
            ) = await asyncio.gather(
                github_service.get_repo_details(owner, repo),
                github_service.get_commits(owner, repo, per_page=50),
                github_service.get_contributors(owner, repo, per_page=30),
                github_service.get_issues(owner, repo, state="all", per_page=50),
                github_service.get_pull_requests(owner, repo, state="all", per_page=50),
                github_service.get_releases(owner, repo, per_page=20),
                github_service.get_branches(owner, repo, per_page=30),
                return_exceptions=True,
            )

            # CRITICAL: If metadata failed, repository access or GitHub API failed completely.
            # Do NOT treat this as successful with empty data!
            if isinstance(meta_res, Exception):
                logger.error(f"Critical GitHub API error fetching repo details for {owner}/{repo}: {meta_res}")
                twin.status = "ERROR"
                twin.error_message = str(meta_res)
                db.commit()
                raise meta_res

            meta = meta_res if isinstance(meta_res, dict) else {}
            category_status["metadata"] = "COLLECTED" if meta else "FAILED"

            # Evaluate each category response
            if isinstance(commits_res, Exception):
                logger.warning(f"Failed fetching commits for {owner}/{repo}: {commits_res}")
                category_status["commits"] = "FAILED"
                raw_commits = [c for c in existing_commits.values()]  # preserve existing
            else:
                raw_commits = commits_res if isinstance(commits_res, list) else []
                category_status["commits"] = "COLLECTED" if raw_commits else "EMPTY"

            if isinstance(contribs_res, Exception):
                logger.warning(f"Failed fetching contributors for {owner}/{repo}: {contribs_res}")
                category_status["contributors"] = "FAILED"
                raw_contribs = [c for c in existing_contribs.values()]
            else:
                raw_contribs = contribs_res if isinstance(contribs_res, list) else []
                category_status["contributors"] = "COLLECTED" if raw_contribs else "EMPTY"

            if isinstance(issues_res, Exception):
                logger.warning(f"Failed fetching issues for {owner}/{repo}: {issues_res}")
                category_status["issues"] = "FAILED"
                raw_issues = [i for i in existing_issues.values()]
            else:
                raw_issues = issues_res if isinstance(issues_res, list) else []
                category_status["issues"] = "COLLECTED" if raw_issues else "EMPTY"

            if isinstance(prs_res, Exception):
                logger.warning(f"Failed fetching pull requests for {owner}/{repo}: {prs_res}")
                category_status["pull_requests"] = "FAILED"
                raw_prs = [p for p in existing_prs.values()]
            else:
                raw_prs = prs_res if isinstance(prs_res, list) else []
                category_status["pull_requests"] = "COLLECTED" if raw_prs else "EMPTY"

            if isinstance(releases_res, Exception):
                logger.warning(f"Failed fetching releases for {owner}/{repo}: {releases_res}")
                category_status["releases"] = "FAILED"
                raw_releases = [r for r in existing_releases.values()]
            else:
                raw_releases = releases_res if isinstance(releases_res, list) else []
                category_status["releases"] = "COLLECTED" if raw_releases else "EMPTY"

            if isinstance(branches_res, Exception):
                logger.warning(f"Failed fetching branches for {owner}/{repo}: {branches_res}")
                category_status["branches"] = "FAILED"
                raw_branches = [b for b in existing_branches.values()]
            else:
                raw_branches = branches_res if isinstance(branches_res, list) else []
                category_status["branches"] = "COLLECTED" if raw_branches else "EMPTY"

            default_branch = meta.get("default_branch", project.default_branch or "main")

            # Tree fetch
            try:
                raw_tree = await github_service.get_repo_tree(owner, repo, tree_sha=default_branch)
                category_status["files"] = "COLLECTED" if raw_tree else "EMPTY"
            except Exception as e:
                logger.warning(f"Failed fetching git tree for {owner}/{repo}: {e}")
                category_status["files"] = "FAILED"
                raw_tree = []

        # Determine overall sync outcome state: ACTIVE or PARTIAL_SUCCESS
        has_partial_failures = any(v == "FAILED" for v in category_status.values())
        sync_final_status = "PARTIAL_SUCCESS" if has_partial_failures else "ACTIVE"

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
            if category_status.get("commits") != "FAILED":
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
                            timestamp=ensure_utc(parse_iso_datetime(cm.get("commit", {}).get("author", {}).get("date"))) or now,
                            actor_login=author_login,
                            actor_avatar_url=(cm.get("author") or {}).get("avatar_url"),
                            source=source,
                            event_metadata={"sha": sha, "html_url": cm.get("html_url")},
                        ))
                if new_commit_count > 0:
                    summary_messages.append(f"{new_commit_count} new commit(s) detected")

            # B. Issues
            if category_status.get("issues") != "FAILED":
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
                            timestamp=ensure_utc(parse_iso_datetime(iss.get("created_at"))) or now,
                            actor_login=user_login,
                            actor_avatar_url=user_avatar,
                            source=source,
                            event_metadata={"number": num, "html_url": iss.get("html_url")},
                        ))
                    else:
                        prev_state = existing_issues[num].state
                        if prev_state != state:
                            ev_type = "ISSUE_CLOSED" if state == "closed" else "ISSUE_OPENED"
                            if state == "closed":
                                closed_issue_count += 1
                            detected_changes.append(DigitalTwinChange(
                                digital_twin_id=twin.id,
                                entity_type="issue",
                                entity_id=str(num),
                                change_type="STATE_CHANGED",
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
                                timestamp=ensure_utc(parse_iso_datetime(iss.get("closed_at"))) or now,
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
            if category_status.get("pull_requests") != "FAILED":
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
                            timestamp=ensure_utc(parse_iso_datetime(pr.get("created_at"))) or now,
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
                                timestamp=ensure_utc(parse_iso_datetime(pr.get("merged_at"))) or now,
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
            if category_status.get("contributors") != "FAILED":
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
            if category_status.get("branches") != "FAILED":
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
            if category_status.get("releases") != "FAILED":
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
                            timestamp=ensure_utc(parse_iso_datetime(r.get("published_at"))) or now,
                            actor_login=rel_author,
                            actor_avatar_url=(r.get("author") or {}).get("avatar_url"),
                            source=source,
                        ))
                if new_release_count > 0:
                    summary_messages.append(f"{new_release_count} new release(s)")

            # G. Repository files / tree
            if category_status.get("files") != "FAILED" and raw_tree:
                new_file_count = 0
                for item in raw_tree[:500]:
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

            # H. Repository metadata changes
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
            twin.status = sync_final_status
            twin.error_message = None
            project.last_synced_at = now
            github_service.record_sync_time()
            project.status = "synced"
            db.commit()
            db.refresh(twin)
            logger.info(f"Sync complete for {project.full_name}: No changes detected. Idempotent version kept at v{twin.current_version}.")
            return {
                "twin_id": twin.id,
                "project_id": project.id,
                "previous_version": twin.current_version,
                "current_version": twin.current_version,
                "status": sync_final_status,
                "changes_detected": 0,
                "changes_summary": ["No repository changes detected."],
                "message": "No repository changes detected. Digital Twin state is current.",
                "synced_at": now,
                "data_coverage": twin.fidelity_score,
                "health_score": project.health_score,
            }

        # 4. PERSIST UPDATED ENTITIES INTO DATABASE SAFELY
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
        project.repo_created_at = ensure_utc(parse_iso_datetime(meta.get("created_at")))
        project.repo_updated_at = ensure_utc(parse_iso_datetime(meta.get("updated_at")))
        project.repo_pushed_at = ensure_utc(parse_iso_datetime(meta.get("pushed_at")))

        # Only overwrite categories if they were successfully fetched!
        if category_status.get("commits") != "FAILED":
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
                    author_date=ensure_utc(parse_iso_datetime(author_info.get("date"))),
                    author_login=gh_author.get("login"),
                    author_avatar_url=gh_author.get("avatar_url"),
                    html_url=cm.get("html_url"),
                ))

        if category_status.get("contributors") != "FAILED":
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

        if category_status.get("issues") != "FAILED":
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
                    created_at=ensure_utc(parse_iso_datetime(iss.get("created_at"))),
                    closed_at=ensure_utc(parse_iso_datetime(iss.get("closed_at"))),
                    html_url=iss.get("html_url"),
                ))

        if category_status.get("pull_requests") != "FAILED":
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
                    created_at=ensure_utc(parse_iso_datetime(pr.get("created_at"))),
                    updated_at=ensure_utc(parse_iso_datetime(pr.get("updated_at"))),
                    merged_at=ensure_utc(parse_iso_datetime(pr.get("merged_at"))),
                    closed_at=ensure_utc(parse_iso_datetime(pr.get("closed_at"))),
                    html_url=pr.get("html_url"),
                ))
            project.open_prs_count = open_pr_count

        if category_status.get("releases") != "FAILED":
            db.query(Release).filter(Release.project_id == project.id).delete()
            for rel in raw_releases:
                rel_author = rel.get("author") or {}
                db.add(Release(
                    project_id=project.id,
                    github_id=rel.get("id"),
                    tag_name=rel.get("tag_name", "v0.0.0"),
                    name=rel.get("name") or rel.get("tag_name"),
                    author_login=rel_author.get("login"),
                    published_at=ensure_utc(parse_iso_datetime(rel.get("published_at"))),
                    html_url=rel.get("html_url"),
                    is_prerelease=rel.get("prerelease", False),
                ))

        if category_status.get("branches") != "FAILED":
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

        if category_status.get("files") != "FAILED" and raw_tree:
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
        github_service.record_sync_time()
        project.status = "synced"

        # 5. INCREMENT TWIN VERSION & CREATE SNAPSHOT
        previous_version = twin.current_version
        if is_initial:
            new_version = 1
        else:
            new_version = previous_version + 1

        twin.current_version = new_version
        twin.last_synced_at = now
        twin.status = sync_final_status
        twin.error_message = None

        entity_counts = {
            "metadata": 1,
            "commits": len(raw_commits),
            "contributors": len(raw_contribs),
            "issues": len(raw_issues),
            "pull_requests": len(raw_prs),
            "branches": len(raw_branches),
            "releases": len(raw_releases),
            "files": len(raw_tree[:500]) if raw_tree else 0,
        }

        data_coverage, _ = self.calculate_data_coverage(entity_counts, category_status=category_status, is_initialized=True)
        twin.fidelity_score = data_coverage if data_coverage is not None else 0.0

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
            "data_coverage": data_coverage,
            "sync_status": sync_final_status,
            "category_status": category_status,
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
        db.flush()

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
            description=f"Snapshot v{new_version} recorded with {len(detected_changes)} detected changes. (Status: {sync_final_status})",
            timestamp=now,
            source=source,
            event_metadata={
                "version_from": previous_version,
                "version_to": new_version,
                "change_count": len(detected_changes),
                "data_coverage": data_coverage,
            }
        ))

        db.commit()
        db.refresh(twin)
        db.refresh(snapshot)

        # Trigger Phase 4 Software Health & Risk Evaluation if available
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
            "status": sync_final_status,
            "changes_detected": len(detected_changes),
            "changes_summary": summary_messages or ["Repository state synchronized."],
            "message": f"Digital Twin synchronized: v{previous_version} → v{new_version}. {len(detected_changes)} changes detected.",
            "synced_at": now,
            "data_coverage": data_coverage,
            "health_score": project.health_score,
        }

    def get_current_state(self, project_id: int, db: Session) -> Dict[str, Any]:
        """
        Retrieves the complete current Digital Twin state for a project with
        real Data Coverage breakdown and deterministic Digital Twin Health Score.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        twin = self.get_or_create_twin(project_id, db)

        # Entity counts from database
        commit_count = db.query(Commit).filter(Commit.project_id == project_id).count()
        contributor_count = db.query(Contributor).filter(Contributor.project_id == project_id).count()
        issue_count = db.query(Issue).filter(Issue.project_id == project_id).count()
        pr_count = db.query(PullRequest).filter(PullRequest.project_id == project_id).count()
        branch_count = db.query(Branch).filter(Branch.project_id == project_id).count()
        release_count = db.query(Release).filter(Release.project_id == project_id).count()
        file_count = db.query(RepositoryFile).filter(RepositoryFile.project_id == project_id).count()

        entity_counts = {
            "metadata": 1 if twin.status != "NOT_INITIALIZED" else 0,
            "commits": commit_count,
            "contributors": contributor_count,
            "issues": issue_count,
            "pull_requests": pr_count,
            "branches": branch_count,
            "releases": release_count,
            "files": file_count,
        }

        data_coverage, data_coverage_components = self.calculate_data_coverage(
            entity_counts,
            is_initialized=(twin.status != "NOT_INITIALIZED")
        )

        snapshots = (
            db.query(DigitalTwinSnapshot)
            .filter(DigitalTwinSnapshot.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinSnapshot.version))
            .all()
        )
        snapshot_count = len(snapshots)
        latest_snapshot = snapshots[0] if snapshots else None

        twin_health_score, twin_health_details = self.calculate_twin_health_score(
            twin=twin,
            data_coverage=data_coverage,
            snapshot_count=snapshot_count,
            project=project,
            entity_counts=entity_counts,
        )

        twin_data = self.get_twin_response_data(twin, db=db)
        twin_data["data_coverage"] = data_coverage
        twin_data["health_score"] = twin_health_score
        twin_data["health_details"] = twin_health_details

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
            "date": format_iso_utc(latest_commit_obj.author_date),
        } if latest_commit_obj else None

        latest_release = {
            "tag": latest_release_obj.tag_name,
            "name": latest_release_obj.name,
            "published_at": format_iso_utc(latest_release_obj.published_at),
        } if latest_release_obj else None

        recent_changes = (
            db.query(DigitalTwinChange)
            .filter(DigitalTwinChange.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinChange.detected_at))
            .limit(40)
            .all()
        )

        recent_events = (
            db.query(DigitalTwinEvent)
            .filter(DigitalTwinEvent.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinEvent.timestamp))
            .limit(40)
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
            "fidelity_components": data_coverage_components,
            "data_coverage": data_coverage,
            "data_coverage_components": data_coverage_components,
            "health_score": twin_health_score,
            "health_breakdown": twin_health_details,
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
        Compares two snapshot versions for a specific project.
        Calculates:
        - Older snapshot metadata and date
        - Newer snapshot metadata and date
        - Added entities
        - Removed entities
        - Modified entities (updated & state_changed)
        - Unchanged entities count
        - Changes grouped by entity category
        Validates both snapshots belong to the same repository.
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
                "older_snapshot": None,
                "newer_snapshot": None,
                "added": [],
                "updated": [],
                "removed": [],
                "unchanged_count": 0,
                "changes_by_category": {},
                "summary": {"message": "No snapshots recorded yet. Synchronize repository to create snapshots."},
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

        # Determine older vs newer
        older = s_from if s_from.version <= s_to.version else s_to
        newer = s_to if s_to.version >= s_from.version else s_from

        older_info = {
            "id": older.id,
            "version": older.version,
            "created_at": format_iso_utc(older.created_at),
            "source": older.source,
            "summary": older.summary,
            "entity_counts": older.entity_counts or {},
        }
        newer_info = {
            "id": newer.id,
            "version": newer.version,
            "created_at": format_iso_utc(newer.created_at),
            "source": newer.source,
            "summary": newer.summary,
            "entity_counts": newer.entity_counts or {},
        }

        # Retrieve changes in snapshots between (older.version, newer.version]
        target_snapshot_ids = [s.id for s in all_snapshots if older.version < s.version <= newer.version]
        changes_between: List[DigitalTwinChange] = []
        if target_snapshot_ids:
            changes_between = (
                db.query(DigitalTwinChange)
                .filter(DigitalTwinChange.snapshot_id.in_(target_snapshot_ids))
                .order_by(DigitalTwinChange.detected_at.desc())
                .all()
            )

        added = []
        updated = []
        removed = []
        category_breakdown: Dict[str, Dict[str, int]] = {}

        for chg in changes_between:
            cat = chg.entity_type
            if cat not in category_breakdown:
                category_breakdown[cat] = {"added": 0, "updated": 0, "removed": 0}

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
                category_breakdown[cat]["added"] += 1
            elif chg.change_type in ("UPDATED", "STATE_CHANGED"):
                updated.append(item)
                category_breakdown[cat]["updated"] += 1
            elif chg.change_type == "DELETED":
                removed.append(item)
                category_breakdown[cat]["removed"] += 1

        counts_older = older.entity_counts or {}
        counts_newer = newer.entity_counts or {}
        diff_counts = {}
        all_keys = set(list(counts_older.keys()) + list(counts_newer.keys()))
        for k in all_keys:
            diff_counts[k] = counts_newer.get(k, 0) - counts_older.get(k, 0)

        total_older_entities = sum(counts_older.values())
        unchanged_count = max(0, total_older_entities - len(removed) - len(updated))

        return {
            "project_id": project_id,
            "twin_id": twin.id,
            "v_from": older.version,
            "v_to": newer.version,
            "older_snapshot": older_info,
            "newer_snapshot": newer_info,
            "added": added,
            "updated": updated,
            "removed": removed,
            "unchanged_count": unchanged_count,
            "changes_by_category": category_breakdown,
            "summary": {
                "total_added": len(added),
                "total_updated": len(updated),
                "total_removed": len(removed),
                "unchanged_count": unchanged_count,
                "entity_count_diffs": diff_counts,
                "version_span": f"v{older.version} → v{newer.version}",
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
            "metadata": 1 if twin.status != "NOT_INITIALIZED" else 0,
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
            {"entity": "Repository Metadata", "count": counts["metadata"], "description": "Repository core settings & properties"},
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
