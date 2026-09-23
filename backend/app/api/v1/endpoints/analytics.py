import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.analytics_service import analytics_service

logger = logging.getLogger("digital_twin.api.analytics")
router = APIRouter()


@router.get(
    "/projects/{project_id}/health",
    summary="Get Software Health Analysis",
    description="Returns detailed health metrics: commit velocity, PR rates, issue resolution, contributor stats, and release history.",
)
async def get_software_health(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return analytics_service.get_software_health(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Health analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/risks",
    summary="Get Risk Analysis",
    description="Returns software risk signals derived from commit patterns, contributor concentration, stale issues, stuck PRs, and release health.",
)
async def get_risk_analysis(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return analytics_service.get_risk_analysis(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Risk analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/evolution",
    summary="Get Software Evolution Timeline",
    description="Returns monthly commit activity, contributor growth curves, release milestones, and project lifecycle timeline.",
)
async def get_evolution(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return analytics_service.get_evolution_data(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Evolution analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/technical-debt",
    summary="Get Technical Debt Analysis",
    description="Derives proxy technical debt signals from issue backlog, PR cycle times, branch proliferation, code churn rates, and documentation gaps.",
)
async def get_technical_debt(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return analytics_service.get_technical_debt(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Technical debt analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/digital-twin",
    summary="Get Digital Twin State",
    description="Returns the current Digital Twin state model: entity map, layer status, fidelity score, sync health, and repository snapshot.",
)
async def get_digital_twin_state(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return analytics_service.get_digital_twin_state(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Digital twin state failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
