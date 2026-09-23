import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.schemas.software_health import (
    SoftwareHealthResponse,
    HealthDimensionResponse,
    HealthHistoryPoint,
)
from app.services.health.health_service import health_service

logger = logging.getLogger("digital_twin.api.health")
router = APIRouter()


@router.get(
    "/projects/{project_id}/health",
    response_model=SoftwareHealthResponse,
    summary="Get Latest Software Health Index",
    description="Returns the latest explainable software engineering health snapshot with all evaluated dimensions.",
)
async def get_software_health(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    snapshot = health_service.get_latest_health(project_id, db)
    if not snapshot:
        # Calculate initial snapshot on-demand if not yet computed
        try:
            snapshot = health_service.calculate_and_persist_health(project_id, db)
        except Exception as e:
            logger.error(f"Error computing health for project {project_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to calculate health: {str(e)}")

    dimensions = [
        HealthDimensionResponse(
            id=d.id,
            dimension=d.dimension,
            name=d.name,
            score=d.score,
            weight=d.weight,
            status=d.status,
            metrics=d.metrics,
            explanation=d.explanation,
        )
        for d in snapshot.dimensions
    ]

    return SoftwareHealthResponse(
        id=snapshot.id,
        project_id=snapshot.project_id,
        twin_version=snapshot.twin_version,
        overall_score=snapshot.overall_score,
        overall_status=snapshot.overall_status,
        calculated_at=snapshot.calculated_at,
        calculation_version=snapshot.calculation_version,
        explanations=snapshot.explanations or [],
        dimensions=dimensions,
    )


@router.get(
    "/projects/{project_id}/health/history",
    response_model=List[HealthHistoryPoint],
    summary="Get Historical Health Snapshots",
    description="Returns historical health snapshots ordered chronologically for trend visualization.",
)
async def get_health_history(
    project_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    history = health_service.get_health_history(project_id, db, limit=limit)
    return [
        HealthHistoryPoint(
            id=s.id,
            project_id=s.project_id,
            calculated_at=s.calculated_at,
            overall_score=s.overall_score,
            overall_status=s.overall_status,
            twin_version=s.twin_version,
        )
        for s in history
    ]


@router.get(
    "/projects/{project_id}/health/dimensions",
    response_model=List[HealthDimensionResponse],
    summary="Get Health Dimensions for Latest Snapshot",
    description="Returns dimension breakdown and metrics for the most recent health snapshot.",
)
async def get_health_dimensions(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    dims = health_service.get_health_dimensions(project_id, db)
    return [
        HealthDimensionResponse(
            id=d.id,
            dimension=d.dimension,
            name=d.name,
            score=d.score,
            weight=d.weight,
            status=d.status,
            metrics=d.metrics,
            explanation=d.explanation,
        )
        for d in dims
    ]


@router.post(
    "/projects/{project_id}/health/recalculate",
    response_model=SoftwareHealthResponse,
    summary="Recalculate Software Health",
    description="Forces re-evaluation of all health metrics and persists a new health snapshot.",
)
async def recalculate_health(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    try:
        snapshot = health_service.calculate_and_persist_health(project_id, db)
        dimensions = [
            HealthDimensionResponse(
                id=d.id,
                dimension=d.dimension,
                name=d.name,
                score=d.score,
                weight=d.weight,
                status=d.status,
                metrics=d.metrics,
                explanation=d.explanation,
            )
            for d in snapshot.dimensions
        ]
        return SoftwareHealthResponse(
            id=snapshot.id,
            project_id=snapshot.project_id,
            twin_version=snapshot.twin_version,
            overall_score=snapshot.overall_score,
            overall_status=snapshot.overall_status,
            calculated_at=snapshot.calculated_at,
            calculation_version=snapshot.calculation_version,
            explanations=snapshot.explanations or [],
            dimensions=dimensions,
        )
    except Exception as e:
        logger.error(f"Error recalculating health for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Recalculation failed: {str(e)}")
