from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    projects,
    analytics,
    digital_twin,
    software_health,
    software_risks,
    architecture,
    evolution,
    technical_debt,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(analytics.router)
api_router.include_router(digital_twin.router)
api_router.include_router(software_health.router)
api_router.include_router(software_risks.router)
api_router.include_router(architecture.router)
api_router.include_router(evolution.router)
api_router.include_router(technical_debt.router)
