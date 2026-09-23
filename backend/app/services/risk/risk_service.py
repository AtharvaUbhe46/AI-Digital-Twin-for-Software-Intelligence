import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.risk import SoftwareRisk
from app.models.project import Project
from app.services.risk.risk_engine import risk_engine, RiskEngine

logger = logging.getLogger("digital_twin.risk_service")


class RiskService:
    """
    Manages risk lifecycle, deterministic deduplication, auto-resolution,
    and state transitions.
    """

    def __init__(self, engine: RiskEngine = None):
        self.engine = engine or risk_engine

    def evaluate_and_persist_risks(self, project_id: int, db: Session) -> List[SoftwareRisk]:
        """
        Runs all risk rules, performs deterministic deduplication against existing risks,
        updates active risks, auto-resolves cleared risks, and persists new risks.
        """
        logger.info(f"Starting risk evaluation for project_id={project_id}")
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        detected_results = self.engine.evaluate_rules(project_id, db)
        detected_fingerprints = {r.fingerprint for r in detected_results}
        now = datetime.now(timezone.utc)

        # 1. Fetch all existing risks for this project
        existing_risks = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == project_id).all()
        existing_by_fp = {r.fingerprint: r for r in existing_risks}

        persisted_risks: List[SoftwareRisk] = []

        # 2. Process detected risks
        for res in detected_results:
            if res.fingerprint in existing_by_fp:
                risk = existing_by_fp[res.fingerprint]
                # If it was resolved earlier, reopen it
                if risk.status == "RESOLVED":
                    risk.status = "OPEN"
                    risk.resolved_at = None
                    risk.detected_at = now
                    logger.info(f"Reopened previously resolved risk [{risk.title}]")

                # Update telemetry & evidence without creating duplicate row
                risk.title = res.title
                risk.description = res.description
                risk.severity = res.severity
                risk.detection_rule = res.detection_rule
                risk.metric_value = res.metric_value
                risk.threshold_value = res.threshold_value
                risk.evidence = res.evidence
                risk.affected_entities = res.affected_entities
                persisted_risks.append(risk)
            else:
                # Insert brand new risk
                new_risk = SoftwareRisk(
                    project_id=project_id,
                    risk_type=res.risk_type,
                    title=res.title,
                    description=res.description,
                    severity=res.severity,
                    status="OPEN",
                    fingerprint=res.fingerprint,
                    detection_rule=res.detection_rule,
                    metric_value=res.metric_value,
                    threshold_value=res.threshold_value,
                    evidence=res.evidence,
                    affected_entities=res.affected_entities,
                    detected_at=now,
                )
                db.add(new_risk)
                persisted_risks.append(new_risk)
                logger.info(f"Created new risk [{new_risk.title}] ({new_risk.severity})")

        # 3. Auto-resolve risks whose condition is no longer present
        for risk in existing_risks:
            if risk.status in ("OPEN", "ACKNOWLEDGED") and risk.fingerprint not in detected_fingerprints:
                risk.status = "RESOLVED"
                risk.resolved_at = now
                logger.info(f"Auto-resolved risk [{risk.title}] as condition is no longer detected.")

        db.commit()
        for r in persisted_risks:
            db.refresh(r)

        logger.info(f"Risk evaluation complete for project {project_id}. Total active: {len([r for r in persisted_risks if r.status != 'RESOLVED'])}")
        return persisted_risks

    def get_risks(
        self,
        project_id: int,
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        risk_type: Optional[str] = None,
    ) -> List[SoftwareRisk]:
        """Returns filtered risk records with strict project isolation."""
        query = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == project_id)

        if status:
            query = query.filter(SoftwareRisk.status == status.upper())
        if severity:
            query = query.filter(SoftwareRisk.severity == severity.upper())
        if risk_type:
            query = query.filter(SoftwareRisk.risk_type == risk_type)

        return query.order_by(desc(SoftwareRisk.detected_at)).all()

    def get_risk_by_id(self, risk_id: int, project_id: int, db: Session) -> Optional[SoftwareRisk]:
        """Fetches a specific risk ensuring project isolation."""
        return db.query(SoftwareRisk).filter(
            SoftwareRisk.id == risk_id,
            SoftwareRisk.project_id == project_id
        ).first()

    def acknowledge_risk(self, risk_id: int, project_id: int, db: Session) -> SoftwareRisk:
        """Transitions risk from OPEN to ACKNOWLEDGED."""
        risk = self.get_risk_by_id(risk_id, project_id, db)
        if not risk:
            raise ValueError(f"Risk with ID {risk_id} not found in this project.")

        if risk.status != "OPEN":
            raise ValueError(f"Cannot acknowledge risk in '{risk.status}' status (must be 'OPEN').")

        risk.status = "ACKNOWLEDGED"
        risk.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(risk)
        logger.info(f"Risk [{risk.id}] acknowledged by user.")
        return risk

    def resolve_risk(self, risk_id: int, project_id: int, db: Session) -> SoftwareRisk:
        """Transitions risk from OPEN or ACKNOWLEDGED to RESOLVED."""
        risk = self.get_risk_by_id(risk_id, project_id, db)
        if not risk:
            raise ValueError(f"Risk with ID {risk_id} not found in this project.")

        if risk.status not in ("OPEN", "ACKNOWLEDGED"):
            raise ValueError(f"Cannot resolve risk in '{risk.status}' status.")

        risk.status = "RESOLVED"
        risk.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(risk)
        logger.info(f"Risk [{risk.id}] manually marked as resolved.")
        return risk


risk_service = RiskService()
