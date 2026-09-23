from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    JSON,
    ForeignKey,
    DateTime,
    Index,
)
from sqlalchemy.orm import relationship, backref
from app.models.base import TimeStampedModel, utc_now


class SoftwareHealthSnapshot(TimeStampedModel):
    """
    Persisted Software Health Snapshot representing the health index and
    engineering quality dimensions at a specific point in time.
    """
    __tablename__ = "software_health_snapshots"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    twin_version = Column(Integer, nullable=True)
    overall_score = Column(Float, nullable=False)
    overall_status = Column(String(50), nullable=False, index=True)
    # Statuses: HEALTHY, ATTENTION, DEGRADED, CRITICAL
    calculated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    calculation_version = Column(String(20), default="1.0.0", nullable=False)
    explanations = Column(JSON, nullable=True)  # List of summary explanation bullets

    # Relationships
    project = relationship("Project", backref=backref("health_snapshots", cascade="all, delete-orphan", order_by="desc(SoftwareHealthSnapshot.calculated_at)"))
    dimensions = relationship("HealthDimensionResult", back_populates="snapshot", cascade="all, delete-orphan", order_by="HealthDimensionResult.dimension")

    __table_args__ = (
        Index("ix_shs_project_calculated", "project_id", "calculated_at"),
    )


class HealthDimensionResult(TimeStampedModel):
    """
    Individual health dimension result associated with a specific Software Health Snapshot.
    Captures metrics, normalized score, weights, and explainable evaluation notes.
    """
    __tablename__ = "health_dimension_results"

    snapshot_id = Column(Integer, ForeignKey("software_health_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    dimension = Column(String(50), nullable=False, index=True)
    # Dimensions: activity, issues, pull_requests, contributors, releases, change_stability, maintenance
    name = Column(String(100), nullable=False)
    score = Column(Float, nullable=True)  # Null if status is INSUFFICIENT_DATA
    weight = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), nullable=False)  # HEALTHY, ATTENTION, DEGRADED, CRITICAL, INSUFFICIENT_DATA
    metrics = Column(JSON, nullable=True)  # Raw computed metrics dictionary
    explanation = Column(JSON, nullable=True)  # List of bullet explanations

    # Relationships
    snapshot = relationship("SoftwareHealthSnapshot", back_populates="dimensions")

    __table_args__ = (
        Index("ix_hdr_snapshot_dimension", "snapshot_id", "dimension"),
    )
