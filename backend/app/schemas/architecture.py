from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class GraphNodeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: Optional[int] = None
    project_id: int
    node_type: str
    name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    language: Optional[str] = None
    module: Optional[str] = None
    node_metadata: Optional[Dict[str, Any]] = None


class GraphEdgeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    analysis_id: Optional[int] = None
    project_id: int
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float = 1.0
    edge_metadata: Optional[Dict[str, Any]] = None


class KnowledgeGraphResponse(BaseModel):
    nodes: List[GraphNodeSchema]
    edges: List[GraphEdgeSchema]
    total_nodes: int
    total_edges: int
    node_type_counts: Dict[str, int] = Field(default_factory=dict)
    relationship_type_counts: Dict[str, int] = Field(default_factory=dict)
    filtered_by: Optional[Dict[str, Any]] = None


class ArchitectureAnalysisStatusResponse(BaseModel):
    analysis_id: Optional[int] = None
    project_id: int
    status: str
    analyzed_at: Optional[datetime] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
    twin_version: Optional[int] = None


class ModuleCouplingMetric(BaseModel):
    module: str
    afferent_coupling: int  # Ca: incoming dependencies
    efferent_coupling: int  # Ce: outgoing dependencies
    instability: float       # I = Ce / (Ca + Ce)
    total_files: int
    dependents: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


class ArchitectureOverviewResponse(BaseModel):
    project_id: int
    analysis_id: int
    analyzed_at: datetime
    total_files: int
    total_modules: int
    total_classes: int
    total_functions: int
    internal_dependencies_count: int
    external_dependencies_count: int
    modules: List[ModuleCouplingMetric]
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)
    hotspots: List[Dict[str, Any]] = Field(default_factory=list)


class CircularDependencyItem(BaseModel):
    cycle_id: str
    length: int
    nodes: List[str]
    path: List[str]
    affected_files: List[str]
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    explanation: str


class CircularDependenciesResponse(BaseModel):
    project_id: int
    analysis_id: int
    total_cycles: int
    cycles: List[CircularDependencyItem]


class PackageDependencyItem(BaseModel):
    name: str
    version: Optional[str] = None
    declared_in: str
    files_using: List[str] = Field(default_factory=list)
    usage_count: int = 0
    is_unused: bool = False


class DependencyAnalysisResponse(BaseModel):
    project_id: int
    analysis_id: int
    packages: List[PackageDependencyItem]
    total_packages: int
    unused_packages_count: int
    internal_deps_count: int
    external_deps_count: int
    dependency_chains: List[List[str]] = Field(default_factory=list)


class ArchitectureMetricsResponse(BaseModel):
    project_id: int
    analysis_id: int
    total_files: int
    total_modules: int
    total_classes: int
    total_functions: int
    total_dependencies: int
    internal_dependencies: int
    external_dependencies: int
    circular_dependencies: int
    architecture_hotspots: int
    most_connected_modules: List[Dict[str, Any]] = Field(default_factory=list)
    most_depended_modules: List[Dict[str, Any]] = Field(default_factory=list)


class NodeDetailResponse(BaseModel):
    node: GraphNodeSchema
    incoming_edges: List[GraphEdgeSchema]
    outgoing_edges: List[GraphEdgeSchema]
    dependencies: List[GraphNodeSchema]
    dependents: List[GraphNodeSchema]
    metrics: Optional[Dict[str, Any]] = None


class AnalyzeRequest(BaseModel):
    repo_path: Optional[str] = None
    force_refresh: bool = False
