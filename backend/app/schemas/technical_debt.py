"""
Pydantic response schemas for Technical Debt Intelligence endpoints (Phase 6).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


from pydantic import BaseModel, ConfigDict


# ─── Sub-models ─────────────────────────────────────────────────────────────────

class DebtIndicatorComponent(BaseModel):
    model_config = ConfigDict(extra='allow')

    name: str
    weight: float
    raw_score: Optional[float] = 0.0
    weighted_score: Optional[float] = 0.0
    evidence: Any = None
    formula: Optional[str] = ""



class DebtMetrics(BaseModel):
    total_commits: int
    fix_commits: int
    fix_ratio_pct: float
    open_issues: int
    stale_issues: int
    total_branches: int
    non_default_branches: int
    slow_prs: int
    total_merged_prs: int


class CommitTypeItem(BaseModel):
    type: str
    count: int
    percentage: float


class InvestigationHotspot(BaseModel):
    path: str
    change_count: int
    churn: int
    contributor_count: int
    last_changed_at: Optional[str] = None
    associated_open_issues: int
    investigation_score: float
    signal: str


class IssueAgeDistribution(BaseModel):
    range_label: str
    count: int
    percentage: float


class OldestIssue(BaseModel):
    number: int
    title: str
    created_at: str
    days_open: float
    html_url: Optional[str] = None


class OldestPR(BaseModel):
    number: int
    title: str
    created_at: str
    days_open: float
    html_url: Optional[str] = None


class PRAgeBucket(BaseModel):
    range_label: str
    count: int
    percentage: float


class BranchInfo(BaseModel):
    name: str
    is_protected: bool
    is_default: bool


class DependencyItemSchema(BaseModel):
    name: str
    version_spec: Optional[str] = None
    is_dev_dependency: bool


class ManifestSchema(BaseModel):
    manifest_type: str
    file_path: str
    dependency_count: int
    detected_at: Optional[str] = None
    items: List[DependencyItemSchema]


# ─── Top-level Response Models ──────────────────────────────────────────────────

class TechnicalDebtSummaryResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    indicator_title: str
    composite_score: float
    level: str
    indicators: List[DebtIndicatorComponent]
    weights: Dict[str, float]
    formula_description: str
    limitations: str
    metrics: DebtMetrics
    debt_categories: List[Dict[str, Any]]
    commit_type_breakdown: List[CommitTypeItem]
    refactoring_candidates: List[Dict[str, Any]]
    total_estimated_debt_hours: float
    overall_debt_score: float
    debt_level: str


class IssueAgeAnalysisResponse(BaseModel):
    project_id: int
    total_open_issues: int
    median_age_days: float
    oldest_issue: Optional[OldestIssue] = None
    distribution: List[IssueAgeDistribution]
    long_lived_count_90d: int
    framing_notice: str


class PRAgeAnalysisResponse(BaseModel):
    project_id: int
    total_open_prs: int
    median_open_age_days: float
    oldest_open_pr: Optional[OldestPR] = None
    age_distribution: List[PRAgeBucket]
    merge_turnaround: Dict[str, Any]
    framing_notice: str


class BranchAgeAnalysisResponse(BaseModel):
    project_id: int
    total_branches: int
    non_default_branches: int
    protected_branches: int
    branches: List[BranchInfo]
    api_limitation_notice: str
    framing_notice: str


class InvestigationHotspotsResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    hotspots: List[InvestigationHotspot]
    definition: str
    framing_notice: str


class DependenciesResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    total_manifests: int
    total_declared_dependencies: int
    manifests: List[ManifestSchema]
    limitation_notice: str
