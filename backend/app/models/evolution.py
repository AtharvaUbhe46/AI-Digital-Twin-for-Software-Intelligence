"""
Evolution & Technical Debt SQLAlchemy models for Phase 6.

These tables persist computed snapshots, file-level change hotspot telemetry,
heuristic technical debt indicators, and dependency manifests.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    DateTime,
    BigInteger,
)
from sqlalchemy.orm import relationship
from app.models.base import TimeStampedModel


class EvolutionSnapshot(TimeStampedModel):
    """
    Periodic snapshot of evolution metrics for a project.
    Stored so historical trends can be served without re-computing every time.
    """
    __tablename__ = "evolution_snapshots"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Snapshot counters (matching sync_service usage)
    commit_count = Column(Integer, default=0)
    contributor_count = Column(Integer, default=0)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    closed_issues = Column(Integer, default=0)
    open_prs = Column(Integer, default=0)
    merged_prs = Column(Integer, default=0)
    release_count = Column(Integer, default=0)
    branch_count = Column(Integer, default=0)

    # Velocity indicator
    velocity_score = Column(Float, default=0.0)
    velocity_rating = Column(String(50), nullable=True)  # "High", "Moderate", "Low"

    project = relationship("Project", foreign_keys=[project_id])


class ChangeHotspot(TimeStampedModel):
    """
    Tracks cumulative file-level change volume metrics across all synced commits.
    Classified as 'Change Hotspot' — active maintenance indicators, NOT defective files.
    """
    __tablename__ = "change_hotspots"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(1024), nullable=False)                   # File path within repo
    change_count = Column(Integer, default=0)                     # Total commits that touched this file
    additions = Column(Integer, default=0)                        # Cumulative lines added
    deletions = Column(Integer, default=0)                        # Cumulative lines deleted
    churn = Column(Integer, default=0)                            # additions + deletions
    contributor_count = Column(Integer, default=1)                # Unique contributors who touched this file
    last_changed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", foreign_keys=[project_id])


class TechnicalDebtIndicator(TimeStampedModel):
    """
    Persists per-indicator rows for the technical debt composite.
    One row per indicator per project (deleted and re-inserted on each sync).
    """
    __tablename__ = "technical_debt_indicators"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Per-indicator fields (matching sync_service usage)
    indicator_type = Column(String(100), nullable=False)          # e.g. "issue_backlog_age"
    indicator_name = Column(String(255), nullable=True)
    score = Column(Float, default=0.0)
    weight = Column(Float, default=0.0)
    severity = Column(String(50), nullable=True)                  # "low", "medium", "high"
    evidence = Column(JSON, nullable=True)                        # Raw evidence dict

    project = relationship("Project", foreign_keys=[project_id])


class DependencyManifest(TimeStampedModel):
    """
    Detected dependency manifest file in the repository (e.g. package.json, requirements.txt).
    Populated during sync by fetching known manifest file paths via the GitHub Contents API.
    """
    __tablename__ = "dependency_manifests"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    manifest_type = Column(String(100), nullable=False)    # "npm", "pip", "maven", "gradle", "gem", "cargo"
    file_path = Column(String(512), nullable=False)        # Path inside the repo
    raw_content = Column(Text, nullable=True)              # Raw content (truncated to 64KB)
    detected_at = Column(DateTime(timezone=True), nullable=True)
    dependency_count = Column(Integer, default=0)

    items = relationship("DependencyItem", back_populates="manifest", cascade="all, delete-orphan")
    project = relationship("Project", foreign_keys=[project_id])


class DependencyItem(TimeStampedModel):
    """
    Parsed individual dependency declared in a DependencyManifest.
    """
    __tablename__ = "dependency_items"

    manifest_id = Column(Integer, ForeignKey("dependency_manifests.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version_spec = Column(String(100), nullable=True)      # Declared version range/constraint
    is_dev_dependency = Column(Boolean, default=False)

    manifest = relationship("DependencyManifest", back_populates="items")
