import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Digital Twin System for Software Intelligence"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    VERSION: str = "0.1.0"

    # Server settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # GitHub API Configuration (Optional token for higher rate limits)
    GITHUB_TOKEN: Union[str, None] = None

    # Digital Twin Core configuration
    DIGITAL_TWIN_STALE_MINUTES: int = 60

    # Phase 4: Software Health & Risk Detection Configuration
    HEALTH_RECENT_DAYS: int = 30
    HEALTH_STALE_ISSUE_DAYS: int = 30
    HEALTH_STALE_PR_DAYS: int = 14
    HEALTH_ACTIVITY_WEIGHT: float = 0.20
    HEALTH_ISSUE_WEIGHT: float = 0.20
    HEALTH_PR_WEIGHT: float = 0.20
    HEALTH_CONTRIBUTOR_WEIGHT: float = 0.15
    HEALTH_RELEASE_WEIGHT: float = 0.10
    HEALTH_MAINTENANCE_WEIGHT: float = 0.15

    RISK_INACTIVITY_DAYS: int = 14
    RISK_STALE_ISSUE_DAYS: int = 30
    RISK_STALE_PR_DAYS: int = 14
    RISK_BACKLOG_WINDOW_DAYS: int = 30
    RISK_ISSUE_BACKLOG_THRESHOLD: int = 5
    RISK_PR_BACKLOG_THRESHOLD: int = 3
    RISK_CONTRIBUTOR_CONCENTRATION_THRESHOLD: float = 0.65
    RISK_RELEASE_STAGNATION_DAYS: int = 90
    RISK_ACTIVITY_SPIKE_MULTIPLIER: float = 3.0

    # PostgreSQL Database configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "software_digital_twin"
    DATABASE_URL: Union[str, None] = None

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
