from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ProjectConnectRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL or slug (e.g. 'https://github.com/facebook/react' or 'facebook/react')")


class ContributorSchema(BaseModel):
    id: int
    login: str
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None
    contributions: int = 0
    contributor_type: str = "User"

    model_config = ConfigDict(from_attributes=True)


class CommitSchema(BaseModel):
    id: int
    sha: str
    message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    author_date: Optional[datetime] = None
    author_login: Optional[str] = None
    author_avatar_url: Optional[str] = None
    html_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IssueSchema(BaseModel):
    id: int
    number: int
    title: str
    state: str
    author_login: Optional[str] = None
    author_avatar_url: Optional[str] = None
    labels: Optional[List[str]] = None
    comments_count: int = 0
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    html_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PullRequestSchema(BaseModel):
    id: int
    number: int
    title: str
    state: str
    author_login: Optional[str] = None
    author_avatar_url: Optional[str] = None
    is_merged: bool = False
    draft: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    html_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReleaseSchema(BaseModel):
    id: int
    tag_name: str
    name: Optional[str] = None
    author_login: Optional[str] = None
    published_at: Optional[datetime] = None
    html_url: Optional[str] = None
    is_prerelease: bool = False

    model_config = ConfigDict(from_attributes=True)


class BranchSchema(BaseModel):
    id: int
    name: str
    commit_sha: Optional[str] = None
    is_protected: bool = False
    is_default: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProjectEventSchema(BaseModel):
    id: int
    event_type: str
    title: str
    actor_login: Optional[str] = None
    actor_avatar_url: Optional[str] = None
    event_time: Optional[datetime] = None
    html_url: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    id: int
    github_owner: str
    github_repo: str
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    default_branch: str = "main"
    language: Optional[str] = None
    visibility: str = "public"
    stars_count: int = 0
    forks_count: int = 0
    watchers_count: int = 0
    open_issues_count: int = 0
    open_prs_count: int = 0
    license_name: Optional[str] = None
    repo_created_at: Optional[datetime] = None
    repo_updated_at: Optional[datetime] = None
    repo_pushed_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    is_active: bool = True
    health_score: float = 0.0
    status: str = "synced"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthIndexComponent(BaseModel):
    name: str
    weight: str
    score: float
    max_score: float
    detail: str


class HealthIndexDetails(BaseModel):
    score: float
    formula: str
    components: List[HealthIndexComponent]


class TimelineDataPoint(BaseModel):
    date: str
    commits: int
    pull_requests: int


class LiveDashboardResponse(BaseModel):
    project_id: int
    full_name: str
    health_score: float
    health_index: Optional[HealthIndexDetails] = None
    total_commits: int
    total_contributors: int
    open_pull_requests: int
    open_issues: int
    last_synced_at: Optional[datetime] = None
    risk_modules_status: str
    activity_timeline: List[TimelineDataPoint]
    recent_activity: List[ProjectEventSchema]


class RepoIdentity(BaseModel):
    name: str
    owner: str
    repo: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    default_branch: str
    language: Optional[str] = None
    visibility: str
    license_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None


class RepoStatistics(BaseModel):
    stars: int
    forks: int
    watchers: int
    open_issues: int
    open_prs: int
    commits_count: int
    contributors_count: int
    releases_count: int


class ProjectOverviewResponse(BaseModel):
    project_id: int
    identity: RepoIdentity
    statistics: RepoStatistics
    contributors: List[ContributorSchema]
    branches: List[BranchSchema]
    releases: List[ReleaseSchema]
    recent_issues: List[IssueSchema]
    recent_pull_requests: List[PullRequestSchema]
