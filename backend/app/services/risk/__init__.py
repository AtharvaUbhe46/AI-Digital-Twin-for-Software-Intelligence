"""
Risk Detection Domain Service Package for AI Digital Twin.
Provides deterministic, explainable risk detection rules, deduplication, and lifecycle management.
"""
from app.services.risk.risk_service import RiskService, risk_service

__all__ = ["RiskService", "risk_service"]
