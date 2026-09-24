from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    JSON,
    ForeignKey,
    DateTime,
    Index,
)
from sqlalchemy.orm import relationship, backref
from app.models.base import TimeStampedModel, utc_now


class ArchitectureAnalysis(TimeStampedModel):
    """
    Persisted Architecture Analysis snapshot for a repository.
    Tracks overall status (QUEUED, ANALYZING, COMPLETED, FAILED),
    summary metrics, detected circular dependencies, and execution logs.
    """
    __tablename__ = "architecture_analyses"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    twin_version = Column(Integer, nullable=True)
    status = Column(String(50), default="QUEUED", nullable=False, index=True)
    # Statuses: QUEUED, ANALYZING, COMPLETED, FAILED
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    cycles = Column(JSON, nullable=True)
    analyzed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    analysis_version = Column(String(20), default="1.0.0", nullable=False)

    # Relationships
    project = relationship("Project", backref=backref("architecture_analyses", cascade="all, delete-orphan", order_by="desc(ArchitectureAnalysis.analyzed_at)"))
    nodes = relationship("GraphNode", back_populates="analysis", cascade="all, delete-orphan")
    edges = relationship("GraphEdge", back_populates="analysis", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_arch_project_status", "project_id", "status"),
        Index("ix_arch_project_analyzed", "project_id", "analyzed_at"),
    )


class GraphNode(TimeStampedModel):
    """
    Individual software entity node in the Knowledge Graph.
    Types: repository, directory, file, module, class, function, method, variable, package, api_endpoint
    """
    __tablename__ = "graph_nodes"

    node_pk = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String(255), nullable=False, index=True)  # Deterministic stable ID (e.g., "file:app/main.py")
    analysis_id = Column(Integer, ForeignKey("architecture_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    file_path = Column(String(1024), nullable=True, index=True)
    line_number = Column(Integer, nullable=True)
    language = Column(String(50), nullable=True)
    module = Column(String(255), nullable=True, index=True)
    node_metadata = Column(JSON, nullable=True)

    # Relationships
    analysis = relationship("ArchitectureAnalysis", back_populates="nodes")

    __table_args__ = (
        Index("ix_node_analysis_id", "analysis_id", "id"),
        Index("ix_node_analysis_type", "analysis_id", "node_type"),
        Index("ix_node_analysis_module", "analysis_id", "module"),
    )


class GraphEdge(TimeStampedModel):
    """
    Directed relationship between two software entity nodes.
    Types: CONTAINS, IMPORTS, EXPORTS, CALLS, EXTENDS, IMPLEMENTS, DEPENDS_ON, DEFINES, USES, EXPOSES, ROUTES_TO
    """
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("architecture_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(255), nullable=False, index=True)
    target_id = Column(String(255), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, default=1.0, nullable=False)
    edge_metadata = Column(JSON, nullable=True)

    # Relationships
    analysis = relationship("ArchitectureAnalysis", back_populates="edges")

    __table_args__ = (
        Index("ix_edge_analysis_rel", "analysis_id", "relationship_type"),
        Index("ix_edge_analysis_source", "analysis_id", "source_id"),
        Index("ix_edge_analysis_target", "analysis_id", "target_id"),
    )
