from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    JSON,
    ForeignKey,
    DateTime,
    Index,
)
from sqlalchemy.orm import relationship, backref
from app.models.base import TimeStampedModel, utc_now


class SoftwareRisk(TimeStampedModel):
    """
    Persisted Software Risk detected by deterministic rule-based evaluation of
    repository engineering telemetry and Digital Twin state.
    """
    __tablename__ = "software_risks"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_type = Column(String(100), nullable=False, index=True)
    # Types: REPOSITORY_INACTIVITY, STALE_ISSUES, STALE_PULL_REQUESTS,
    #        ISSUE_BACKLOG_GROWTH, PR_BACKLOG_GROWTH, LOW_CONTRIBUTOR_DIVERSITY,
    #        RELEASE_STAGNATION, ACTIVITY_SPIKE
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    # Severities: LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(20), default="OPEN", nullable=False, index=True)
    # Statuses: OPEN, ACKNOWLEDGED, RESOLVED
    fingerprint = Column(String(255), nullable=False, index=True)
    # Deterministic fingerprint: hash(project_id, risk_type, entity_ref)
    detection_rule = Column(String(100), nullable=False)
    metric_value = Column(String(255), nullable=True)
    threshold_value = Column(String(255), nullable=True)
    evidence = Column(JSON, nullable=True)
    affected_entities = Column(JSON, nullable=True)

    detected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", backref=backref("risks", cascade="all, delete-orphan", order_by="desc(SoftwareRisk.detected_at)"))

    __table_args__ = (
        Index("ix_sr_project_status", "project_id", "status"),
        Index("ix_sr_project_fingerprint", "project_id", "fingerprint"),
        Index("ix_sr_project_severity", "project_id", "severity"),
    )
