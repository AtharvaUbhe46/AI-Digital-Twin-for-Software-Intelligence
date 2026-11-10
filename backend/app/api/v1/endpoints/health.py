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

    # Check GitHub status and populate real rate-limit metrics
    rate_state = github_service.rate_limit_state
    reset_ts = rate_state.get("reset") or 0
    reset_human = None
    if reset_ts:
        secs_left = max(0, reset_ts - int(datetime.now(timezone.utc).timestamp()))
        mins_left = secs_left // 60
        reset_human = f"Resets in {mins_left}m" if mins_left > 0 else "Resets in <1m"

    gh_status = GitHubHealth(
        connected=rate_state.get("connected", True),
        remaining_rate_limit=rate_state.get("remaining", 60),
        limit=rate_state.get("limit", 60),
        used=rate_state.get("used", 0),
        reset_timestamp=reset_ts if reset_ts > 0 else None,
        reset_time_human=reset_human,
        authenticated=rate_state.get("authenticated", bool(settings.GITHUB_TOKEN)),
        status=rate_state.get("status", "connected" if settings.GITHUB_TOKEN else "token_not_configured"),
        resource=rate_state.get("resource", "core"),
        last_synced_at=rate_state.get("last_synced_at"),
    )

    try:
        # Fetch fresh quota status from GitHub API
        rate_info = await github_service.get_rate_limit(force_refresh=True)
        core_rate = rate_info.get("resources", {}).get("core", {})
        if core_rate:
            gh_status.remaining_rate_limit = core_rate.get("remaining", gh_status.remaining_rate_limit)
            gh_status.limit = core_rate.get("limit", gh_status.limit)
            gh_status.used = core_rate.get("used", gh_status.used)
            new_reset = core_rate.get("reset", reset_ts)
            if new_reset:
                gh_status.reset_timestamp = new_reset
                secs_left = max(0, new_reset - int(datetime.now(timezone.utc).timestamp()))
                mins_left = secs_left // 60
                gh_status.reset_time_human = f"Resets in {mins_left}m" if mins_left > 0 else "Resets in <1m"
            gh_status.authenticated = gh_status.limit >= 1000
            gh_status.status = "connected"
            gh_status.connected = True
    except Exception as exc:
        logger_status = github_service.rate_limit_state.get("status", "unreachable")
        gh_status.status = logger_status
        gh_status.connected = logger_status not in ("unreachable", "auth_failed")

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
