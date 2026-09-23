import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.health import SoftwareHealthSnapshot, HealthDimensionResult
from app.models.project import Project
from app.models.digital_twin import DigitalTwin
from app.core.config import settings
from app.services.health.health_metrics import (
    compute_activity_metrics,
    compute_issue_metrics,
    compute_pr_metrics,
    compute_contributor_metrics,
    compute_release_metrics,
    compute_maintenance_metrics,
)
from app.services.health.health_scoring import (
    score_activity,
    score_issues,
    score_pull_requests,
    score_contributors,
    score_releases,
    score_maintenance,
    calculate_overall_health,
)
from app.services.health.health_explanations import (
    explain_activity,
    explain_issues,
    explain_pull_requests,
    explain_contributors,
    explain_releases,
    explain_maintenance,
    generate_overall_explanations,
)

logger = logging.getLogger("digital_twin.health_service")


class HealthService:
    """
    Orchestrates deterministic Software Health evaluation, scoring,
    explanation generation, and snapshot persistence.
    """

    def calculate_and_persist_health(
        self,
        project_id: int,
        db: Session,
        twin_version: Optional[int] = None,
    ) -> SoftwareHealthSnapshot:
        """
        Calculates health metrics, assigns deterministic scores, builds human-readable
        explanations, persists the snapshot and dimension results, and updates project.health_score.
        """
        logger.info(f"Starting Software Health calculation for project_id={project_id}")

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        # Determine digital twin version if not explicitly passed
        if twin_version is None:
            twin = db.query(DigitalTwin).filter(DigitalTwin.project_id == project_id).first()
            if twin:
                twin_version = twin.current_version

        # 1. Compute raw metrics
        act_metrics = compute_activity_metrics(project_id, db)
        iss_metrics = compute_issue_metrics(project_id, db)
        pr_metrics = compute_pr_metrics(project_id, db)
        contrib_metrics = compute_contributor_metrics(project_id, db)
        rel_metrics = compute_release_metrics(project_id, db)
        maint_metrics = compute_maintenance_metrics(project_id, db)

        # 2. Score each dimension
        act_score, act_status = score_activity(act_metrics)
        iss_score, iss_status = score_issues(iss_metrics)
        pr_score, pr_status = score_pull_requests(pr_metrics)
        contrib_score, contrib_status = score_contributors(contrib_metrics)
        rel_score, rel_status = score_releases(rel_metrics)
        maint_score, maint_status = score_maintenance(maint_metrics)

        # 3. Assemble dimension payloads
        dimensions_data = [
            {
                "dimension": "activity",
                "name": "Repository Activity",
                "score": act_score,
                "weight": settings.HEALTH_ACTIVITY_WEIGHT,
                "status": act_status,
                "metrics": act_metrics,
                "explanation": explain_activity(act_metrics),
            },
            {
                "dimension": "issues",
                "name": "Issue Health",
                "score": iss_score,
                "weight": settings.HEALTH_ISSUE_WEIGHT,
                "status": iss_status,
                "metrics": iss_metrics,
                "explanation": explain_issues(iss_metrics),
            },
            {
                "dimension": "pull_requests",
                "name": "Pull Request Health",
                "score": pr_score,
                "weight": settings.HEALTH_PR_WEIGHT,
                "status": pr_status,
                "metrics": pr_metrics,
                "explanation": explain_pull_requests(pr_metrics),
            },
            {
                "dimension": "contributors",
                "name": "Contributor Health",
                "score": contrib_score,
                "weight": settings.HEALTH_CONTRIBUTOR_WEIGHT,
                "status": contrib_status,
                "metrics": contrib_metrics,
                "explanation": explain_contributors(contrib_metrics),
            },
            {
                "dimension": "releases",
                "name": "Release Health",
                "score": rel_score,
                "weight": settings.HEALTH_RELEASE_WEIGHT,
                "status": rel_status,
                "metrics": rel_metrics,
                "explanation": explain_releases(rel_metrics),
            },
            {
                "dimension": "maintenance",
                "name": "Maintenance Health",
                "score": maint_score,
                "weight": settings.HEALTH_MAINTENANCE_WEIGHT,
                "status": maint_status,
                "metrics": maint_metrics,
                "explanation": explain_maintenance(maint_metrics),
            },
        ]

        # 4. Calculate overall weighted score with dynamic re-weighting
        overall_score, overall_status = calculate_overall_health(dimensions_data)
        overall_explanations = generate_overall_explanations(dimensions_data, overall_score, overall_status)

        # 5. Persist Snapshot
        snapshot = SoftwareHealthSnapshot(
            project_id=project_id,
            twin_version=twin_version,
            overall_score=overall_score,
            overall_status=overall_status,
            calculated_at=datetime.now(timezone.utc),
            calculation_version="1.0.0",
            explanations=overall_explanations,
        )
        db.add(snapshot)
        db.flush()

        # 6. Persist Dimension Results
        for d in dimensions_data:
            dim_record = HealthDimensionResult(
                snapshot_id=snapshot.id,
                dimension=d["dimension"],
                name=d["name"],
                score=d["score"],
                weight=d["weight"],
                status=d["status"],
                metrics=d["metrics"],
                explanation=d["explanation"],
            )
            db.add(dim_record)

        # Update Project current health score
        project.health_score = overall_score
        db.commit()
        db.refresh(snapshot)

        logger.info(
            f"Health snapshot saved for project {project_id}: "
            f"score={overall_score}, status={overall_status}, snapshot_id={snapshot.id}"
        )
        return snapshot

    def get_latest_health(self, project_id: int, db: Session) -> Optional[SoftwareHealthSnapshot]:
        """Returns the most recent persisted health snapshot for a project."""
        return (
            db.query(SoftwareHealthSnapshot)
            .filter(SoftwareHealthSnapshot.project_id == project_id)
            .order_by(desc(SoftwareHealthSnapshot.calculated_at))
            .first()
        )

    def get_health_history(self, project_id: int, db: Session, limit: int = 30) -> List[SoftwareHealthSnapshot]:
        """Returns historical health snapshots ordered chronologically for trending."""
        snapshots = (
            db.query(SoftwareHealthSnapshot)
            .filter(SoftwareHealthSnapshot.project_id == project_id)
            .order_by(desc(SoftwareHealthSnapshot.calculated_at))
            .limit(limit)
            .all()
        )
        # Return in ascending order for charting
        return list(reversed(snapshots))

    def get_health_dimensions(self, project_id: int, db: Session) -> List[HealthDimensionResult]:
        """Returns dimension results for the latest snapshot."""
        latest = self.get_latest_health(project_id, db)
        if not latest:
            return []
        return (
            db.query(HealthDimensionResult)
            .filter(HealthDimensionResult.snapshot_id == latest.id)
            .order_by(HealthDimensionResult.dimension)
            .all()
        )


health_service = HealthService()
