from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class HealthDimensionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    dimension: str
    name: str
    score: Optional[float] = None
    weight: float
    status: str
    metrics: Optional[Dict[str, Any]] = None
    explanation: Optional[List[str]] = None


class SoftwareHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    twin_version: Optional[int] = None
    overall_score: float
    overall_status: str
    calculated_at: datetime
    calculation_version: str
    explanations: Optional[List[str]] = None
    dimensions: List[HealthDimensionResponse] = []


class HealthHistoryPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    calculated_at: datetime
    overall_score: float
    overall_status: str
    twin_version: Optional[int] = None
