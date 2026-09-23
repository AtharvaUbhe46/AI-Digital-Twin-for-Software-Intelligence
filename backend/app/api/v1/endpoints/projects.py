import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.project import (
    ProjectConnectRequest,
    ProjectResponse,
    LiveDashboardResponse,
    ProjectOverviewResponse,
)
from app.services.project_service import project_service
from app.services.sync_service import sync_service
from app.services.github_service import (
    GitHubAPIError,
    GitHubRepoNotFoundError,
    GitHubRateLimitError,
    GitHubInvalidURLError,
)

logger = logging.getLogger("digital_twin.api.projects")
router = APIRouter()


@router.post(
    "/projects/connect",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect GitHub Repository",
    description="Validates GitHub URL, fetches repository metadata and initial entities, stores them in PostgreSQL, and sets as active Digital Twin.",
)
async def connect_repository(
    payload: ProjectConnectRequest,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable."
        )

    try:
        project = await project_service.connect_repository(payload.repo_url, db)
        return project
    except GitHubInvalidURLError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except GitHubRepoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except GitHubRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to connect repository {payload.repo_url}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to connect repository: {str(e)}")


@router.get(
    "/projects",
    response_model=List[ProjectResponse],
    summary="List All Connected Projects",
    description="Returns all GitHub projects stored in the Digital Twin database.",
)
async def list_projects(db: Session = Depends(get_db)):
    if not db:
        return []
    return project_service.get_all_projects(db)


@router.get(
    "/projects/active",
    response_model=Optional[ProjectResponse],
    summary="Get Active Project",
    description="Returns the currently active project context for the Digital Twin.",
)
async def get_active_project(db: Session = Depends(get_db)):
    if not db:
        return None
    return project_service.get_active_project(db)


@router.get(
    "/projects/active/dashboard",
    response_model=LiveDashboardResponse,
    summary="Get Active Project Dashboard Metrics",
    description="Returns real dashboard telemetry for the currently active project.",
)
async def get_active_dashboard(db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    active = project_service.get_active_project(db)
    if not active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No repository currently connected.")
    return project_service.get_dashboard_data(active.id, db)


@router.get(
    "/projects/active/overview",
    response_model=ProjectOverviewResponse,
    summary="Get Active Project Overview",
    description="Returns complete overview for the currently active project.",
)
async def get_active_overview(db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    active = project_service.get_active_project(db)
    if not active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No repository currently connected.")
    return project_service.get_project_overview(active.id, db)


@router.post(
    "/projects/{project_id}/activate",
    response_model=ProjectResponse,
    summary="Activate Project Context",
    description="Switches the active Digital Twin context to the specified project ID.",
)
async def activate_project(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return project_service.activate_project(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/projects/{project_id}/sync",
    response_model=ProjectResponse,
    summary="Synchronize Project with GitHub",
    description="Refreshes commits, PRs, issues, contributors, and releases directly from live GitHub API.",
)
async def sync_project(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return await sync_service.sync_repository(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except GitHubRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except GitHubAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Synchronization failed: {str(e)}")


@router.get(
    "/projects/{project_id}/dashboard",
    response_model=LiveDashboardResponse,
    summary="Get Live Dashboard Metrics",
    description="Returns real-time project metrics, commit/PR timeline, health index calculation, and event feed.",
)
async def get_dashboard_data(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return project_service.get_dashboard_data(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/projects/{project_id}/overview",
    response_model=ProjectOverviewResponse,
    summary="Get Real Project Overview",
    description="Returns complete Phase 2 repository overview including identity, statistics, contributors, branches, releases, and issues.",
)
async def get_project_overview(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return project_service.get_project_overview(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect / Delete Project",
    description="Removes the project and its synced records from the Digital Twin system.",
)
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    deleted = project_service.delete_project(project_id, db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return None
