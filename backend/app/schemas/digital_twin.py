from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class DigitalTwinResponse(BaseModel):
    id: int
    project_id: int
    current_version: int
    status: str  # NOT_INITIALIZED, INITIALIZING, ACTIVE, SYNCING, OUTDATED, ERROR
    error_message: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    fidelity_score: float = 0.0
    stale_threshold_minutes: int = 60
    is_outdated: bool = False
    staleness_minutes: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DigitalTwinSnapshotResponse(BaseModel):
    id: int
    digital_twin_id: int
    version: int
    created_at: datetime
    source: str
    summary: Optional[str] = None
    change_count: int = 0
    entity_counts: Optional[Dict[str, int]] = None
    state_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DigitalTwinChangeResponse(BaseModel):
    id: int
    digital_twin_id: int
    snapshot_id: Optional[int] = None
    entity_type: str  # commit, contributor, issue, pull_request, branch, release, file, repository
    entity_id: str
    change_type: str  # CREATED, UPDATED, DELETED, STATE_CHANGED
    change_summary: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    detected_at: datetime
    source: str

    model_config = ConfigDict(from_attributes=True)


class DigitalTwinEventResponse(BaseModel):
    id: int
    digital_twin_id: int
    snapshot_id: Optional[int] = None
    event_type: str  # COMMIT_ADDED, ISSUE_OPENED, ISSUE_CLOSED, PR_OPENED, PR_MERGED, etc.
    entity_type: str
    entity_id: str
    title: str
    description: Optional[str] = None
    timestamp: datetime
    actor_login: Optional[str] = None
    actor_avatar_url: Optional[str] = None
    source: str
    event_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class RepositoryFileSchema(BaseModel):
    id: int
    path: str
    filename: str
    extension: Optional[str] = None
    directory: str
    size: int
    file_type: str
    sha: Optional[str] = None
    latest_commit_sha: Optional[str] = None
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


class DigitalTwinSyncResponse(BaseModel):
    twin_id: int
    project_id: int
    previous_version: int
    current_version: int
    status: str
    changes_detected: int
    changes_summary: List[str]
    message: str
    synced_at: datetime


class EntityDiffItem(BaseModel):
    entity_type: str
    entity_id: str
    change_type: str  # added, updated, removed
    summary: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None


class DigitalTwinCompareResponse(BaseModel):
    project_id: int
    twin_id: int
    v_from: int
    v_to: int
    added: List[EntityDiffItem] = []
    updated: List[EntityDiffItem] = []
    removed: List[EntityDiffItem] = []
    summary: Dict[str, Any] = {}


class DigitalTwinStateResponse(BaseModel):
    twin: DigitalTwinResponse
    repository: Dict[str, Any]
    current_snapshot: Optional[DigitalTwinSnapshotResponse] = None
    entity_counts: Dict[str, int]
    latest_commit: Optional[Dict[str, Any]] = None
    latest_release: Optional[Dict[str, Any]] = None
    current_branch: Optional[str] = None
    fidelity_components: List[Dict[str, Any]]
    recent_changes: List[DigitalTwinChangeResponse] = []
    recent_events: List[DigitalTwinEventResponse] = []


class DigitalTwinEntitiesResponse(BaseModel):
    project_id: int
    twin_id: int
    total_entities: int
    counts: Dict[str, int]
    breakdown: List[Dict[str, Any]]
