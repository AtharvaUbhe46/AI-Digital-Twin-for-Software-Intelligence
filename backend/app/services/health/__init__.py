"""
Software Health Domain Service Package for AI Digital Twin.
Provides deterministic, explainable engineering health metrics, scoring, and explanations.
"""
from app.services.health.health_service import HealthService, health_service

__all__ = ["HealthService", "health_service"]
