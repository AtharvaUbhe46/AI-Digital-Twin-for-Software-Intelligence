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
