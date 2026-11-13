from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class SimulationParameterInput(BaseModel):
    parameter_key: str = Field(..., description="Unique key of the parameter to modify")
    proposed_value: float = Field(..., description="Proposed hypothetical value")
    user_notes: Optional[str] = Field(None, description="Optional explanation or intent for this change")


class SimulationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Name for the hypothetical scenario")
    description: Optional[str] = Field(None, max_length=2000, description="Optional detailed scenario description")
    category: str = Field("custom", description="Scenario category: team, issues, dependencies, activity, custom")
    parameters: List[SimulationParameterInput] = Field(..., min_length=1, description="List of parameter changes")


class SimulationParameterMeta(BaseModel):
    key: str
    name: str
    category: str  # team, issues, dependencies, activity, custom
    unit: str
    current_value: Optional[float] = None
    min_value: float
    max_value: float
    step: float = 1.0
    description: str
    is_available: bool = True
    unavailable_reason: Optional[str] = None


class SimulationBaselineResponse(BaseModel):
    project_id: int
    project_name: str
    full_name: str
    twin_version: int
    snapshot_id: Optional[int] = None
    last_synced_at: Optional[datetime] = None
    metrics: Dict[str, Any]
    available_parameters: List[SimulationParameterMeta]
    health_score: Optional[float] = None
    health_status: str = "INSUFFICIENT_DATA"


class ImpactItemResponse(BaseModel):
    metric_key: str
    metric_name: str
    baseline_value: Any
    simulated_value: Any
    delta: Optional[float] = None
    delta_percentage: Optional[float] = None
    direction: str  # IMPROVEMENT, DETERIORATION, NEUTRAL, INSUFFICIENT_DATA
    reason: str
    methodology: str
    confidence: str  # HIGH, MEDIUM, LOW, INSUFFICIENT_DATA


class HealthImpactResponse(BaseModel):
    baseline_score: Optional[float] = None
    simulated_score: Optional[float] = None
    delta: Optional[float] = None
    baseline_status: str
    simulated_status: str
    dimension_deltas: Dict[str, Any] = Field(default_factory=dict)
    key_factors: List[str] = Field(default_factory=list)


class SimulationRiskItem(BaseModel):
    id: str
    title: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    factor: str


class SimulationOpportunityItem(BaseModel):
    id: str
    title: str
    description: str
    impact: str  # LOW, MEDIUM, HIGH
    factor: str


class AIExplanationResponse(BaseModel):
    summary: str
    what_changed: str
    predicted_outcomes: str
    why_it_happens: str
    positive_aspects: List[str] = Field(default_factory=list)
    potential_issues: List[str] = Field(default_factory=list)
    strategic_recommendations: List[str] = Field(default_factory=list)
    is_ai_generated: bool = False
    provider: str = "deterministic"


class SimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    category: str
    status: str
    baseline_twin_version: Optional[int] = None
    baseline_snapshot_id: Optional[int] = None
    baseline_metrics: Dict[str, Any]
    parameters: List[Dict[str, Any]]
    simulated_metrics: Dict[str, Any]
    impact_analysis: List[ImpactItemResponse]
    health_impact: HealthImpactResponse
    risks: List[SimulationRiskItem]
    opportunities: List[SimulationOpportunityItem]
    ai_explanation: AIExplanationResponse
    execution_duration_ms: float
    created_at: datetime


class SimulationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    category: str
    status: str
    baseline_twin_version: Optional[int] = None
    health_score_delta: Optional[float] = None
    parameter_count: int
    risk_count: int
    opportunity_count: int
    summary_headline: str
    created_at: datetime


class SimulationCompareResponse(BaseModel):
    project_id: int
    project_name: str
    simulation_a: SimulationResponse
    simulation_b: SimulationResponse
    parameter_differences: List[Dict[str, Any]]
    metric_comparisons: List[Dict[str, Any]]
    health_comparison: Dict[str, Any]
    risk_tradeoffs: Dict[str, Any]
    comparative_summary: str

