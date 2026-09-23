from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.core.database import check_db_connection
from app.schemas.health import HealthResponse, DatabaseHealth, GitHubHealth
from app.services.github_service import github_service

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System, Database & GitHub Health Check",
    description="Returns API status, version, uptime timestamp, active PostgreSQL connection health, and GitHub API quota status.",
)
async def health_check():
    is_connected, latency_ms, error_msg = check_db_connection()

    db_status = DatabaseHealth(
        connected=is_connected,
        status="connected" if is_connected else "disconnected",
        latency_ms=latency_ms,
        error=error_msg,
    )

    # Check GitHub status
    gh_status = GitHubHealth(connected=True, remaining_rate_limit=60, limit=60, authenticated=bool(settings.GITHUB_TOKEN))
    try:
        rate_info = await github_service.get_rate_limit()
        core_rate = rate_info.get("resources", {}).get("core", {})
        gh_status.remaining_rate_limit = core_rate.get("remaining", 60)
        gh_status.limit = core_rate.get("limit", 60)
        gh_status.connected = True
    except Exception:
        gh_status.connected = False

    overall_status = "healthy" if (is_connected and gh_status.connected) else "degraded"

    return HealthResponse(
        status=overall_status,
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        github=gh_status,
        details={
            "debug": settings.DEBUG,
            "database_server": settings.POSTGRES_SERVER,
            "database_name": settings.POSTGRES_DB,
            "github_token_configured": bool(settings.GITHUB_TOKEN),
        },
    )
