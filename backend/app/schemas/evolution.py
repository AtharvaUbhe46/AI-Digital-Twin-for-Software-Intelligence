"""
Pydantic response schemas for Software Evolution endpoints (Phase 6).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ─── Shared Sub-models ─────────────────────────────────────────────────────────

class ActivityPeriod(BaseModel):
    period: str
    date_label: str
    commits: int
    prs: int
    issues: int
    releases: int
    contributors: int
    churn: int


class ContributorGrowthPoint(BaseModel):
    month: str
    new_contributors: int
    total_contributors: int


class ContributorTimelinePoint(BaseModel):
    period: str
    date_label: str
    active_contributors: int
    new_contributors: int
    returning_contributors: int


class ContributorDistribution(BaseModel):
    range: str
    contributors: int


class TimelineEvent(BaseModel):
    type: str
    label: str
    date: Optional[str] = None
    actor_login: Optional[str] = None
    actor_avatar_url: Optional[str] = None
    url: Optional[str] = None
    is_prerelease: Optional[bool] = None
    details: Optional[Dict[str, Any]] = None


class ChurnDataPoint(BaseModel):
    period: str
    date_label: str
    additions: int
    deletions: int
    churn: int
    net_growth: int


class PeriodDelta(BaseModel):
    metric: str
    period_a_val: float
    period_b_val: float
    delta_pct: float
    direction: str


class VelocityEvidence(BaseModel):
    recent_commits_30d: int
    merged_prs_30d: int
    total_contributors: int


class VelocityIndicator(BaseModel):
    title: str
    score: float
    rating: str
    formula: str
    evidence: VelocityEvidence
    interpretation: str


class ReleaseMilestone(BaseModel):
    type: str
    label: str
    date: Optional[str] = None
    url: Optional[str] = None
    is_prerelease: Optional[bool] = None


class EvolutionTotals(BaseModel):
    total_commits: int
    total_releases: int
    total_merged_prs: int
    total_contributors: int
    open_issues: int
    open_prs: int


class ChangeHotspotItem(BaseModel):
    id: int
    path: str
    change_count: int
    additions: int
    deletions: int
    churn: int
    contributor_count: int
    last_changed_at: Optional[str] = None


# ─── Top-level Response Models ──────────────────────────────────────────────────

class EvolutionOverviewResponse(BaseModel):
    project_id: int
    project_name: str
    has_sufficient_data: bool
    repo_created_at: Optional[str] = None
    repo_pushed_at: Optional[str] = None
    velocity_indicator: VelocityIndicator
    totals: EvolutionTotals
    monthly_activity: List[ActivityPeriod]
    contributor_growth: List[ContributorGrowthPoint]
    release_milestones: List[ReleaseMilestone]
    timeline_events: List[TimelineEvent]
    latest_snapshot: Optional[Any] = None  # EvolutionSnapshot ORM object


class TimelineResponse(BaseModel):
    project_id: int
    timeframe: str
    has_sufficient_data: bool
    event_count: int
    events: List[TimelineEvent]
    message: Optional[str] = None
    period_start: str
    period_end: str


class CodeChurnResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    formula: str
    interpretation: str
    total_additions: int
    total_deletions: int
    total_churn: int
    net_lines: int
    timeframe: str
    data_points: List[ChurnDataPoint]


class ActivityTrendsResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    weekly: List[ActivityPeriod]
    monthly: List[ActivityPeriod]
    total_commits: int
    total_prs: int
    total_issues: int


class ContributorEvolutionResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    total_unique_contributors: int
    purpose_disclaimer: str
    growth_curve: List[ContributorGrowthPoint]
    timeline: List[ContributorTimelinePoint]
    distribution: List[ContributorDistribution]


class ChangeHotspotsResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    hotspots: List[ChangeHotspotItem]
    total_analyzed_files: int
    definition: str


class PeriodComparisonResponse(BaseModel):
    project_id: int
    has_sufficient_data: bool
    period_a: str
    period_b: str
    deltas: List[PeriodDelta]
    summary: str
