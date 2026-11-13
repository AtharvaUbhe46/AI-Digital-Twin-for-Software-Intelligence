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


class WhatIfSimulation(TimeStampedModel):
    """
    Persisted What-If Simulation record representing a hypothetical scenario evaluation
    against a Digital Twin baseline project state.
    """
    __tablename__ = "what_if_simulations"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="custom", nullable=False, index=True)
    # Categories: team, issues, dependencies, activity, custom

    status = Column(String(50), default="COMPLETED", nullable=False, index=True)
    # Statuses: COMPLETED, FAILED

    # Baseline references
    baseline_twin_version = Column(Integer, nullable=True)
    baseline_snapshot_id = Column(Integer, nullable=True)
    baseline_metrics = Column(JSON, nullable=False)  # snapshot of actual project metrics

    # Inputs
    parameters = Column(JSON, nullable=False)  # List of modified parameter objects

    # Calculated Outputs
    simulated_metrics = Column(JSON, nullable=False)
    impact_analysis = Column(JSON, nullable=False)  # List of ImpactItem objects
    health_impact = Column(JSON, nullable=False)    # HealthImpact object with dimension breakdown
    risks = Column(JSON, nullable=False)            # List of SimulationRiskItem objects
    opportunities = Column(JSON, nullable=False)    # List of SimulationOpportunityItem objects

    # AI & Explanation Outputs
    ai_explanation = Column(JSON, nullable=False)   # AIExplanationResponse object
    execution_duration_ms = Column(Float, default=0.0)

    # Relationship
    project = relationship(
        "Project",
        backref=backref("simulations", cascade="all, delete-orphan", order_by="desc(WhatIfSimulation.created_at)")
    )

    __table_args__ = (
        Index("ix_wis_project_created", "project_id", "created_at"),
        Index("ix_wis_project_category", "project_id", "category"),
    )

