from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class SoftwareRiskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    risk_type: str
    title: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    status: str    # OPEN, ACKNOWLEDGED, RESOLVED
    fingerprint: str
    detection_rule: str
    metric_value: Optional[str] = None
    threshold_value: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    affected_entities: Optional[List[Dict[str, Any]]] = None
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class RiskSummaryResponse(BaseModel):
    total_risks: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    open_count: int
    acknowledged_count: int
    resolved_count: int
