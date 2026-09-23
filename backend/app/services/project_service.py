import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
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
from app.services.github_service import parse_github_url, github_service
from app.services.sync_service import sync_service

logger = logging.getLogger("digital_twin.project_service")


class ProjectService:
    @staticmethod
    async def connect_repository(repo_url: str, db: Session) -> Project:
        """
        Validates GitHub URL, ensures project record in DB, activates it,
        and triggers full initial synchronization with live GitHub data.
        """
        owner, repo = parse_github_url(repo_url)
        full_name = f"{owner}/{repo}"

        project = db.query(Project).filter(Project.full_name.ilike(full_name)).first()

        # Set all other projects to not active
        db.query(Project).update({Project.is_active: False})

        if not project:
            project = Project(
                github_owner=owner,
                github_repo=repo,
                name=repo,
                full_name=full_name,
                html_url=f"https://github.com/{owner}/{repo}",
                is_active=True,
                status="syncing"
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        else:
            project.is_active = True
            project.status = "syncing"
            db.commit()

        # Synchronize live GitHub data into PostgreSQL
        synced_project = await sync_service.sync_repository(project.id, db)

        # Initialize Digital Twin representation (Snapshot v1, state, events)
        try:
            from app.services.digital_twin_service import digital_twin_service
            await digital_twin_service.initialize_twin(project.id, db)
        except Exception as e:
            logger.warning(f"Could not auto-initialize Digital Twin for {full_name}: {e}")

        return synced_project

    @staticmethod
    def get_all_projects(db: Session) -> List[Project]:
        """Returns all connected projects in the database."""
        return db.query(Project).order_by(desc(Project.is_active), desc(Project.updated_at)).all()

    @staticmethod
    def get_active_project(db: Session) -> Optional[Project]:
        """Returns the currently active project or activates the most recent one if available."""
        active = db.query(Project).filter(Project.is_active == True).first()
        if active:
            return active

        # If no project marked active but projects exist, activate the first one
        first_proj = db.query(Project).order_by(desc(Project.updated_at)).first()
        if first_proj:
            first_proj.is_active = True
            db.commit()
            db.refresh(first_proj)
            return first_proj

        return None

    @staticmethod
    def activate_project(project_id: int, db: Session) -> Project:
        """Sets project with project_id as active and deactivates others."""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        db.query(Project).update({Project.is_active: False})
        project.is_active = True
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(project_id: int, db: Session) -> bool:
        """Removes a connected project from the database."""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return False

        was_active = project.is_active
        db.delete(project)
        db.commit()

        if was_active:
            remaining = db.query(Project).first()
            if remaining:
                remaining.is_active = True
                db.commit()

        return True

    @staticmethod
    def get_dashboard_data(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Calculates live dashboard metrics from the active project's normalized data.
        Returns REAL data only. Zero mock numbers.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        # Live metric counts from database
        commit_count = db.query(Commit).filter(Commit.project_id == project_id).count()
        contributor_count = db.query(Contributor).filter(Contributor.project_id == project_id).count()
        open_prs_count = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.state == "open"
        ).count()

        # If no PRs explicitly tracked, use project.open_prs_count
        if open_prs_count == 0 and project.open_prs_count > 0:
            open_prs_count = project.open_prs_count

        # Build real activity timeline from actual commits and PRs (last 7 days)
        now = datetime.now(timezone.utc).date()
        date_map = {}
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i in range(6, -1, -1):
            d = now - timedelta(days=i)
            day_str = d.strftime("%a")
            date_map[d.isoformat()] = {"day": day_str, "commits": 0, "pull_requests": 0}

        # Populate commit counts
        recent_commits = db.query(Commit).filter(
            Commit.project_id == project_id,
            Commit.author_date.isnot(None)
        ).all()

        for c in recent_commits:
            if c.author_date:
                c_date = c.author_date.date().isoformat()
                if c_date in date_map:
                    date_map[c_date]["commits"] += 1

        # Populate PR counts
        recent_prs = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.created_at.isnot(None)
        ).all()

        for pr in recent_prs:
            if pr.created_at:
                pr_date = pr.created_at.date().isoformat()
                if pr_date in date_map:
                    date_map[pr_date]["pull_requests"] += 1

        # Form timeline list
        timeline = [
            {"date": v["day"], "commits": v["commits"], "pull_requests": v["pull_requests"]}
            for v in date_map.values()
        ]

        # Recent events from DB
        events = db.query(ProjectEvent).filter(
            ProjectEvent.project_id == project_id
        ).order_by(desc(ProjectEvent.event_time)).limit(15).all()

        return {
            "project_id": project.id,
            "full_name": project.full_name,
            "health_score": project.health_score,
            "health_index": project.health_index_details,
            "total_commits": commit_count,
            "total_contributors": contributor_count,
            "open_pull_requests": open_prs_count,
            "open_issues": project.open_issues_count,
            "last_synced_at": project.last_synced_at,
            "risk_modules_status": "Requires code analysis integration (Phase 4)",
            "activity_timeline": timeline,
            "recent_activity": events
        }

    @staticmethod
    def get_project_overview(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Returns comprehensive Phase 2 overview for the selected project using 100% real data.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        commit_count = db.query(Commit).filter(Commit.project_id == project_id).count()
        contributor_count = db.query(Contributor).filter(Contributor.project_id == project_id).count()
        releases_count = db.query(Release).filter(Release.project_id == project_id).count()

        contributors = db.query(Contributor).filter(
            Contributor.project_id == project_id
        ).order_by(desc(Contributor.contributions)).limit(30).all()

        branches = db.query(Branch).filter(Branch.project_id == project_id).limit(30).all()
        releases = db.query(Release).filter(Release.project_id == project_id).order_by(desc(Release.published_at)).limit(20).all()
        recent_issues = db.query(Issue).filter(Issue.project_id == project_id).order_by(desc(Issue.created_at)).limit(20).all()
        recent_prs = db.query(PullRequest).filter(PullRequest.project_id == project_id).order_by(desc(PullRequest.created_at)).limit(20).all()

        return {
            "project_id": project.id,
            "identity": {
                "name": project.name,
                "owner": project.github_owner,
                "repo": project.github_repo,
                "full_name": project.full_name,
                "description": project.description,
                "html_url": project.html_url,
                "default_branch": project.default_branch,
                "language": project.language,
                "visibility": project.visibility,
                "license_name": project.license_name,
                "created_at": project.repo_created_at,
                "updated_at": project.repo_updated_at,
                "pushed_at": project.repo_pushed_at,
                "last_synced_at": project.last_synced_at
            },
            "statistics": {
                "stars": project.stars_count,
                "forks": project.forks_count,
                "watchers": project.watchers_count,
                "open_issues": project.open_issues_count,
                "open_prs": project.open_prs_count,
                "commits_count": commit_count,
                "contributors_count": contributor_count,
                "releases_count": releases_count
            },
            "contributors": contributors,
            "branches": branches,
            "releases": releases,
            "recent_issues": recent_issues,
            "recent_pull_requests": recent_prs
        }


project_service = ProjectService()
