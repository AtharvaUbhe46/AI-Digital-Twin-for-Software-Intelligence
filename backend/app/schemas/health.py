from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    connected: bool
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class GitHubHealth(BaseModel):
    connected: bool
    remaining_rate_limit: int = 60
    limit: int = 60
    used: int = 0
    reset_timestamp: Optional[int] = None
    reset_time_human: Optional[str] = None
    authenticated: bool = False
    status: str = "connected"
    resource: Optional[str] = "core"
    last_synced_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status (healthy, degraded, unhealthy)")
    service: str
    version: str
    environment: str
    timestamp: datetime
    database: DatabaseHealth
    github: Optional[GitHubHealth] = None
    details: Optional[Dict[str, Any]] = None
