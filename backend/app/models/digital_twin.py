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
    Index,
)
from sqlalchemy.orm import relationship, backref
from app.models.base import TimeStampedModel, utc_now


class DigitalTwin(TimeStampedModel):
    """
    Maintains the continuously updated Digital Twin identity, version, and lifecycle
    status for a specific software project repository.
    """
    __tablename__ = "digital_twins"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    current_version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="NOT_INITIALIZED", nullable=False, index=True)
    # Statuses: NOT_INITIALIZED, INITIALIZING, ACTIVE, SYNCING, OUTDATED, ERROR
    error_message = Column(Text, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True, index=True)
    fidelity_score = Column(Float, default=0.0)
    stale_threshold_minutes = Column(Integer, default=60, nullable=False)

    # Relationships
    project = relationship("Project", backref=backref("digital_twin", uselist=False, cascade="all, delete-orphan"))
    snapshots = relationship("DigitalTwinSnapshot", back_populates="digital_twin", cascade="all, delete-orphan", order_by="desc(DigitalTwinSnapshot.version)")
    changes = relationship("DigitalTwinChange", back_populates="digital_twin", cascade="all, delete-orphan", order_by="desc(DigitalTwinChange.detected_at)")
    events = relationship("DigitalTwinEvent", back_populates="digital_twin", cascade="all, delete-orphan", order_by="desc(DigitalTwinEvent.timestamp)")


class DigitalTwinSnapshot(TimeStampedModel):
    """
    Historical snapshot of repository state at a particular version.
    Stores immutable state summary, entity counts, and top-level telemetry.
    """
    __tablename__ = "digital_twin_snapshots"

    digital_twin_id = Column(Integer, ForeignKey("digital_twins.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    source = Column(String(50), default="github_sync", nullable=False)  # "initial_sync", "manual_sync", "scheduled_sync"
    summary = Column(Text, nullable=True)
    change_count = Column(Integer, default=0, nullable=False)
    entity_counts = Column(JSON, nullable=True)  # {"commits": 50, "contributors": 12, ...}
    state_data = Column(JSON, nullable=True)     # {"default_branch": "main", "latest_commit_sha": "...", ...}

    # Relationships
    digital_twin = relationship("DigitalTwin", back_populates="snapshots")
    changes = relationship("DigitalTwinChange", back_populates="snapshot", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_twin_snapshot_version", "digital_twin_id", "version", unique=True),
    )


class DigitalTwinChange(TimeStampedModel):
    """
    Normalized change record detected during synchronization.
    Tracks what changed between previous state and new state.
    """
    __tablename__ = "digital_twin_changes"

    digital_twin_id = Column(Integer, ForeignKey("digital_twins.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("digital_twin_snapshots.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # commit, contributor, issue, pull_request, branch, release, file, repository
    entity_id = Column(String(255), nullable=False, index=True)   # SHA, login, PR #, etc.
    change_type = Column(String(50), nullable=False, index=True)  # CREATED, UPDATED, DELETED, STATE_CHANGED
    change_summary = Column(String(512), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    detected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    source = Column(String(50), default="github_sync", nullable=False)

    # Relationships
    digital_twin = relationship("DigitalTwin", back_populates="changes")
    snapshot = relationship("DigitalTwinSnapshot", back_populates="changes")


class DigitalTwinEvent(TimeStampedModel):
    """
    Immutable Digital Twin event stream.
    Tracks chronological occurrences detected from repository activity.
    """
    __tablename__ = "digital_twin_events"

    digital_twin_id = Column(Integer, ForeignKey("digital_twins.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("digital_twin_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # COMMIT_ADDED, ISSUE_OPENED, ISSUE_CLOSED, PR_OPENED, PR_MERGED, etc.
    entity_type = Column(String(50), nullable=False)             # commit, issue, pull_request, branch, release, contributor, file, repository, twin
    entity_id = Column(String(255), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    actor_login = Column(String(255), nullable=True)
    actor_avatar_url = Column(String(512), nullable=True)
    source = Column(String(50), default="github_sync", nullable=False)
    event_metadata = Column(JSON, nullable=True)

    # Relationships
    digital_twin = relationship("DigitalTwin", back_populates="events")


class RepositoryFile(TimeStampedModel):
    """
    Indexed repository file or directory node from Git tree.
    """
    __tablename__ = "repository_files"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(1024), nullable=False, index=True)
    filename = Column(String(255), nullable=False, index=True)
    extension = Column(String(50), nullable=True, index=True)
    directory = Column(String(1024), nullable=False)
    size = Column(Integer, default=0, nullable=False)
    file_type = Column(String(20), default="blob", nullable=False)  # "blob", "tree"
    sha = Column(String(64), nullable=True)
    latest_commit_sha = Column(String(64), nullable=True)
    first_seen = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", backref=backref("files", cascade="all, delete-orphan"))

    __table_args__ = (
        Index("idx_repo_files_project_path", "project_id", "path", unique=True),
    )
