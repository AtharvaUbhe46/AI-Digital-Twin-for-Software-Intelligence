from fastapi import APIRouter
from app.api.v1.endpoints import health, projects, analytics, digital_twin

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(projects.router, tags=["Projects & Dashboard"])
api_router.include_router(digital_twin.router, tags=["Digital Twin Core"])
api_router.include_router(analytics.router, tags=["Analytics"])
