import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.digital_twin import (
    DigitalTwinResponse,
    DigitalTwinStateResponse,
    DigitalTwinSnapshotResponse,
    DigitalTwinChangeResponse,
    DigitalTwinEventResponse,
    DigitalTwinSyncResponse,
    DigitalTwinCompareResponse,
    DigitalTwinEntitiesResponse,
)
from app.services.digital_twin_service import digital_twin_service
from app.services.github_service import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubRepoNotFoundError,
)

logger = logging.getLogger("digital_twin.api.endpoints")
router = APIRouter()


@router.get(
    "/projects/{project_id}/digital-twin",
    response_model=DigitalTwinResponse,
    summary="Get Digital Twin Metadata & Status",
    description="Returns current Digital Twin identity, version counter, lifecycle status, staleness, and fidelity score.",
)
async def get_digital_twin(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        twin = digital_twin_service.get_or_create_twin(project_id, db)
        return digital_twin_service.get_twin_response_data(twin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch digital twin for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/status",
    response_model=DigitalTwinResponse,
    summary="Get Digital Twin Lifecycle Status",
    description="Returns lightweight lifecycle status: ACTIVE, SYNCING, OUTDATED, ERROR, or NOT_INITIALIZED.",
)
async def get_digital_twin_status(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        twin = digital_twin_service.get_or_create_twin(project_id, db)
        return digital_twin_service.get_twin_response_data(twin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/state",
    response_model=DigitalTwinStateResponse,
    summary="Get Complete Digital Twin State",
    description="Returns unified state representation: entity counts, latest commit/release, current snapshot, recent changes, events, and fidelity score.",
)
async def get_digital_twin_state(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return digital_twin_service.get_current_state(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get digital twin state for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/projects/{project_id}/digital-twin/initialize",
    response_model=DigitalTwinSyncResponse,
    summary="Initialize Digital Twin",
    description="Initializes virtual representation for project, captures snapshot v1, and transitions lifecycle to ACTIVE.",
)
async def initialize_digital_twin(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return await digital_twin_service.initialize_twin(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except GitHubRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to initialize digital twin for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/projects/{project_id}/digital-twin/sync",
    response_model=DigitalTwinSyncResponse,
    summary="Synchronize Digital Twin with GitHub",
    description="Pulls live GitHub data, detects state changes vs previous snapshot, generates version increment, records changes/events, or returns idempotent no-change response.",
)
async def sync_digital_twin(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return await digital_twin_service.synchronize_twin(project_id, db, source="manual_sync")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except GitHubRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to sync digital twin for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/snapshots",
    response_model=List[DigitalTwinSnapshotResponse],
    summary="List Historical Snapshots",
    description="Returns chronological version history of snapshots for this project's Digital Twin.",
)
async def get_digital_twin_snapshots(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return digital_twin_service.get_snapshots(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/snapshots/{snapshot_id}",
    summary="Get Specific Snapshot Detail",
    description="Returns detailed telemetry and change records recorded at a particular snapshot version.",
)
async def get_digital_twin_snapshot_detail(project_id: int, snapshot_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return digital_twin_service.get_snapshot_detail(project_id, snapshot_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/compare",
    response_model=DigitalTwinCompareResponse,
    summary="Compare Two Digital Twin Snapshot Versions",
    description="Calculates state difference between two versions (v_from and v_to), categorizing additions, updates, and removals.",
)
async def compare_digital_twin_versions(
    project_id: int,
    v_from: Optional[int] = Query(None, description="Starting version for comparison"),
    v_to: Optional[int] = Query(None, description="Target version for comparison"),
    db: Session = Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return digital_twin_service.compare_snapshots(project_id, v_from=v_from, v_to=v_to, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Version comparison failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/changes",
    response_model=List[DigitalTwinChangeResponse],
    summary="Get Detected Changes Feed",
    description="Returns detected changes records with change types, summaries, and old/new values.",
)
async def get_digital_twin_changes(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    snapshot_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return digital_twin_service.get_changes(project_id, db, limit=limit, snapshot_id=snapshot_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/events",
    response_model=List[DigitalTwinEventResponse],
    summary="Get Digital Twin Event Timeline",
    description="Returns chronological events recorded for this Digital Twin.",
)
async def get_digital_twin_events(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return digital_twin_service.get_events(project_id, db, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin/entities",
    response_model=DigitalTwinEntitiesResponse,
    summary="Get Digital Twin Tracked Entities",
    description="Returns counts and structured breakdown of all tracked entity types (commits, contributors, issues, PRs, branches, releases, files).",
)
async def get_digital_twin_entities(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return digital_twin_service.get_entities_summary(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
