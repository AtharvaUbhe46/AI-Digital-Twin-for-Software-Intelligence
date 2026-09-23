from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    DateTime,
    BigInteger,
)
from sqlalchemy.orm import relationship
from app.models.base import TimeStampedModel


class Project(TimeStampedModel):
    __tablename__ = "projects"

    github_owner = Column(String(255), nullable=False, index=True)
    github_repo = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False, unique=True, index=True)  # "owner/repo"
    description = Column(Text, nullable=True)
    html_url = Column(String(512), nullable=False)
    default_branch = Column(String(100), default="main")
    language = Column(String(100), nullable=True)
    visibility = Column(String(50), default="public")
    stars_count = Column(Integer, default=0)
    forks_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)
    open_issues_count = Column(Integer, default=0)
    open_prs_count = Column(Integer, default=0)
    network_count = Column(Integer, default=0)
    subscribers_count = Column(Integer, default=0)
    license_name = Column(String(100), nullable=True)

    repo_created_at = Column(DateTime(timezone=True), nullable=True)
    repo_updated_at = Column(DateTime(timezone=True), nullable=True)
    repo_pushed_at = Column(DateTime(timezone=True), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True)
    health_score = Column(Float, default=0.0)
    health_index_details = Column(JSON, nullable=True)
    status = Column(String(50), default="synced")  # "synced", "syncing", "error"

    # Normalized relational collections
    contributors = relationship("Contributor", back_populates="project", cascade="all, delete-orphan", order_by="desc(Contributor.contributions)")
    commits = relationship("Commit", back_populates="project", cascade="all, delete-orphan", order_by="desc(Commit.author_date)")
    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan", order_by="desc(Issue.created_at)")
    pull_requests = relationship("PullRequest", back_populates="project", cascade="all, delete-orphan", order_by="desc(PullRequest.created_at)")
    releases = relationship("Release", back_populates="project", cascade="all, delete-orphan", order_by="desc(Release.published_at)")
    branches = relationship("Branch", back_populates="project", cascade="all, delete-orphan")
    events = relationship("ProjectEvent", back_populates="project", cascade="all, delete-orphan", order_by="desc(ProjectEvent.event_time)")


class Contributor(TimeStampedModel):
    __tablename__ = "contributors"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    github_id = Column(BigInteger, nullable=True)
    login = Column(String(255), nullable=False, index=True)
    avatar_url = Column(String(512), nullable=True)
    html_url = Column(String(512), nullable=True)
    contributions = Column(Integer, default=0)
    contributor_type = Column(String(50), default="User")

    project = relationship("Project", back_populates="contributors")


class Commit(TimeStampedModel):
    __tablename__ = "commits"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    sha = Column(String(64), nullable=False, index=True)
    message = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=True)
    author_email = Column(String(255), nullable=True)
    author_date = Column(DateTime(timezone=True), nullable=True, index=True)
    author_login = Column(String(255), nullable=True)
    author_avatar_url = Column(String(512), nullable=True)
    html_url = Column(String(512), nullable=True)

    project = relationship("Project", back_populates="commits")


class Issue(TimeStampedModel):
    __tablename__ = "issues"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    github_id = Column(BigInteger, nullable=True)
    number = Column(Integer, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    state = Column(String(50), default="open", index=True)  # "open", "closed"
    author_login = Column(String(255), nullable=True)
    author_avatar_url = Column(String(512), nullable=True)
    labels = Column(JSON, nullable=True)
    comments_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    html_url = Column(String(512), nullable=True)

    project = relationship("Project", back_populates="issues")


class PullRequest(TimeStampedModel):
    __tablename__ = "pull_requests"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    github_id = Column(BigInteger, nullable=True)
    number = Column(Integer, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    state = Column(String(50), default="open", index=True)  # "open", "closed"
    author_login = Column(String(255), nullable=True)
    author_avatar_url = Column(String(512), nullable=True)
    is_merged = Column(Boolean, default=False)
    draft = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    merged_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    html_url = Column(String(512), nullable=True)

    project = relationship("Project", back_populates="pull_requests")


class Release(TimeStampedModel):
    __tablename__ = "releases"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    github_id = Column(BigInteger, nullable=True)
    tag_name = Column(String(100), nullable=False)
    name = Column(String(255), nullable=True)
    author_login = Column(String(255), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    html_url = Column(String(512), nullable=True)
    is_prerelease = Column(Boolean, default=False)

    project = relationship("Project", back_populates="releases")


class Branch(TimeStampedModel):
    __tablename__ = "branches"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    commit_sha = Column(String(64), nullable=True)
    is_protected = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    project = relationship("Project", back_populates="branches")


class ProjectEvent(TimeStampedModel):
    __tablename__ = "project_events"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # "commit", "pr_open", "pr_merge", "issue_open", "release"
    title = Column(String(512), nullable=False)
    actor_login = Column(String(255), nullable=True)
    actor_avatar_url = Column(String(512), nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=True, index=True)
    html_url = Column(String(512), nullable=True)
    event_metadata = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="events")
