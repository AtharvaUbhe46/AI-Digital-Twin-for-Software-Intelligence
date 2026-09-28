import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.evolution_service import evolution_service
from app.services.hotspot_service import hotspot_service
from app.schemas.evolution import (
    EvolutionOverviewResponse,
    TimelineResponse,
    CodeChurnResponse,
    ActivityTrendsResponse,
    ContributorEvolutionResponse,
    ChangeHotspotsResponse,
    PeriodComparisonResponse,
)

logger = logging.getLogger("digital_twin.api.evolution")
router = APIRouter()


@router.get(
    "/projects/{project_id}/evolution",
    response_model=EvolutionOverviewResponse,
    summary="Get Software Evolution Overview",
    description="Returns high-level project evolution model: development velocity indicator, monthly activities, contributor growth, and milestone markers.",
)
async def get_evolution_overview(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return evolution_service.get_evolution_overview(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Evolution overview failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/evolution/timeline",
    response_model=TimelineResponse,
    summary="Get Software Evolution Timeline",
    description="Returns filtered chronological events for the specified timeframe (7d, 30d, 90d, 6m, 1y). If data is sparse, returns has_sufficient_data: False.",
)
async def get_timeline(
    project_id: int,
    timeframe: str = Query("30d", regex="^(7d|30d|90d|6m|1y|all)$"),
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return evolution_service.get_timeline(project_id, db, timeframe=timeframe)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Evolution timeline failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/evolution/churn",
    response_model=CodeChurnResponse,
    summary="Get Repository Code Churn",
    description="Calculates code churn as Lines Added + Lines Deleted over defined intervals. Presented as an observable volume signal.",
)
async def get_code_churn(
    project_id: int,
    timeframe: str = Query("30d", regex="^(7d|30d|90d|6m|1y|all)$"),
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return evolution_service.get_code_churn(project_id, db, timeframe=timeframe)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Code churn calculation failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/evolution/activity",
    response_model=ActivityTrendsResponse,
    summary="Get Activity Trends",
    description="Returns periodic weekly and monthly frequency of commits, PRs, issues, releases, and active contributors.",
)
async def get_activity_trends(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return evolution_service.get_activity_trends(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Activity trends calculation failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/evolution/contributors",
    response_model=ContributorEvolutionResponse,
    summary="Get Contributor Evolution",
    description="Analyzes developer continuity over time: active, new, and returning contributors. Strictly non-evaluative; no individual rankings.",
)
async def get_contributor_evolution(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return evolution_service.get_contributor_evolution(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Contributor evolution calculation failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/evolution/hotspots",
    response_model=ChangeHotspotsResponse,
    summary="Get Change Hotspots",
    description="Returns files and modules with frequent revisions, additions, and deletions. Classified as Change Hotspots, not defective code.",
)
async def get_change_hotspots(
    project_id: int,
    sort_by: str = Query("changes", regex="^(changes|churn|recent|contributors)$"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return hotspot_service.get_change_hotspots(project_id, db, limit=limit, sort_by=sort_by)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Change hotspots query failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/evolution/compare",
    response_model=PeriodComparisonResponse,
    summary="Compare Historical Periods",
    description="Compares metrics between Period A and Period B. Computes real +/- percentage deltas.",
)
async def compare_periods(
    project_id: int,
    period_a: str = Query("30d", regex="^(7d|30d|90d|6m|1y)$"),
    period_b: str = Query("60d", regex="^(7d|30d|90d|6m|1y)$"),
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return evolution_service.compare_periods(project_id, db, period_a=period_a, period_b=period_b)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Period comparison failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
