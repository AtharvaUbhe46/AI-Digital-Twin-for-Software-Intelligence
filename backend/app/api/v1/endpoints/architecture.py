import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.schemas.architecture import (
    KnowledgeGraphResponse,
    ArchitectureAnalysisStatusResponse,
    ArchitectureOverviewResponse,
    CircularDependenciesResponse,
    DependencyAnalysisResponse,
    ArchitectureMetricsResponse,
    NodeDetailResponse,
    AnalyzeRequest,
    GraphNodeSchema,
    GraphEdgeSchema,
    ModuleCouplingMetric,
    CircularDependencyItem,
    PackageDependencyItem,
)
from app.services.architecture.architecture_service import architecture_service

logger = logging.getLogger("digital_twin.api.architecture")
router = APIRouter()


@router.post(
    "/projects/{project_id}/architecture/analyze",
    response_model=ArchitectureAnalysisStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Architecture & Knowledge Graph Analysis",
    description="Executes AST-based code analysis, constructs knowledge graph, evaluates module coupling, and detects cycles.",
)
async def analyze_project_architecture(
    project_id: int,
    payload: Optional[AnalyzeRequest] = None,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    try:
        repo_path = payload.repo_path if payload else None
        force_refresh = payload.force_refresh if payload else True
        analysis = architecture_service.analyze_project(
            project_id=project_id,
            db=db,
            repo_path=repo_path,
            force_refresh=force_refresh
        )
        return ArchitectureAnalysisStatusResponse(
            analysis_id=analysis.id,
            project_id=project_id,
            status=analysis.status,
            analyzed_at=analysis.analyzed_at,
            summary=analysis.summary,
            error_message=analysis.error_message,
            twin_version=analysis.twin_version,
        )
    except Exception as e:
        logger.error(f"Architecture analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/architecture/status",
    response_model=ArchitectureAnalysisStatusResponse,
    summary="Get Architecture Analysis Status",
    description="Returns current status of architecture analysis for the project.",
)
async def get_architecture_status(
    project_id: int,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    analysis = architecture_service.get_latest_analysis(project_id, db)
    if not analysis:
        # Auto-trigger if none exists
        analysis = architecture_service.analyze_project(project_id, db)

    return ArchitectureAnalysisStatusResponse(
        analysis_id=analysis.id,
        project_id=project_id,
        status=analysis.status,
        analyzed_at=analysis.analyzed_at,
        summary=analysis.summary,
        error_message=analysis.error_message,
        twin_version=analysis.twin_version,
    )


@router.get(
    "/projects/{project_id}/architecture/graph",
    response_model=KnowledgeGraphResponse,
    summary="Get Filtered Knowledge Graph",
    description="Returns software entity nodes and relationships with filtering by node type, relation, module, and search.",
)
async def get_knowledge_graph(
    project_id: int,
    node_type: Optional[str] = Query(None, description="Filter by node type: file, class, function, package, api_endpoint, directory"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship: IMPORTS, CONTAINS, CALLS, EXTENDS, DEPENDS_ON, ROUTES_TO"),
    module: Optional[str] = Query(None, description="Filter by module"),
    search: Optional[str] = Query(None, description="Search nodes by name"),
    limit: int = Query(500, ge=1, le=2000, description="Max nodes to return"),
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    try:
        data = architecture_service.get_knowledge_graph(
            project_id=project_id,
            db=db,
            node_type=node_type,
            relationship_type=relationship_type,
            module=module,
            search=search,
            limit=limit,
        )
        return KnowledgeGraphResponse(
            nodes=[GraphNodeSchema.model_validate(n) for n in data["nodes"]],
            edges=[GraphEdgeSchema.model_validate(e) for e in data["edges"]],
            total_nodes=data["total_nodes"],
            total_edges=data["total_edges"],
            node_type_counts=data["node_type_counts"],
            relationship_type_counts=data["relationship_type_counts"],
            filtered_by=data["filtered_by"],
        )
    except Exception as e:
        logger.error(f"Error fetching knowledge graph for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/architecture/overview",
    response_model=ArchitectureOverviewResponse,
    summary="Get High-Level Software Architecture View",
    description="Returns module coupling indicators (Ca, Ce, Instability), architectural bottlenecks, and hotspots.",
)
async def get_architecture_overview(
    project_id: int,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    analysis = architecture_service.get_latest_analysis(project_id, db)
    if not analysis or analysis.status != "COMPLETED":
        analysis = architecture_service.analyze_project(project_id, db)

    metrics = analysis.metrics or {}
    modules_raw = metrics.get("modules", [])

    return ArchitectureOverviewResponse(
        project_id=project_id,
        analysis_id=analysis.id,
        analyzed_at=analysis.analyzed_at,
        total_files=metrics.get("total_files", 0),
        total_modules=metrics.get("total_modules", 0),
        total_classes=metrics.get("total_classes", 0),
        total_functions=metrics.get("total_functions", 0),
        internal_dependencies_count=metrics.get("internal_dependencies", 0),
        external_dependencies_count=metrics.get("external_dependencies", 0),
        modules=[ModuleCouplingMetric(**m) for m in modules_raw],
        bottlenecks=metrics.get("bottlenecks", []),
        hotspots=metrics.get("hotspots", []),
    )


@router.get(
    "/projects/{project_id}/architecture/dependencies",
    response_model=DependencyAnalysisResponse,
    summary="Get Dependency Analysis & External Packages",
    description="Returns direct and external package dependencies, usage breakdown, and detects unused dependencies.",
)
async def get_dependencies_analysis(
    project_id: int,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    analysis = architecture_service.get_latest_analysis(project_id, db)
    if not analysis or analysis.status != "COMPLETED":
        analysis = architecture_service.analyze_project(project_id, db)

    metrics = analysis.metrics or {}
    packages_raw = metrics.get("packages", [])

    return DependencyAnalysisResponse(
        project_id=project_id,
        analysis_id=analysis.id,
        packages=[PackageDependencyItem(**p) for p in packages_raw],
        total_packages=len(packages_raw),
        unused_packages_count=metrics.get("unused_packages_count", 0),
        internal_deps_count=metrics.get("internal_dependencies", 0),
        external_deps_count=metrics.get("external_dependencies", 0),
    )


@router.get(
    "/projects/{project_id}/architecture/cycles",
    response_model=CircularDependenciesResponse,
    summary="Get Detected Circular Dependencies",
    description="Returns graph-detected circular dependency chains with exact cycle paths and severity assessments.",
)
async def get_circular_dependencies(
    project_id: int,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    analysis = architecture_service.get_latest_analysis(project_id, db)
    if not analysis or analysis.status != "COMPLETED":
        analysis = architecture_service.analyze_project(project_id, db)

    cycles_raw = analysis.cycles or []

    return CircularDependenciesResponse(
        project_id=project_id,
        analysis_id=analysis.id,
        total_cycles=len(cycles_raw),
        cycles=[CircularDependencyItem(**c) for c in cycles_raw],
    )


@router.get(
    "/projects/{project_id}/architecture/metrics",
    response_model=ArchitectureMetricsResponse,
    summary="Get Architecture Summary Metrics",
    description="Returns aggregate metrics: files, modules, classes, functions, cycles, and most connected components.",
)
async def get_architecture_metrics(
    project_id: int,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    analysis = architecture_service.get_latest_analysis(project_id, db)
    if not analysis or analysis.status != "COMPLETED":
        analysis = architecture_service.analyze_project(project_id, db)

    metrics = analysis.metrics or {}

    return ArchitectureMetricsResponse(
        project_id=project_id,
        analysis_id=analysis.id,
        total_files=metrics.get("total_files", 0),
        total_modules=metrics.get("total_modules", 0),
        total_classes=metrics.get("total_classes", 0),
        total_functions=metrics.get("total_functions", 0),
        total_dependencies=metrics.get("total_dependencies", 0),
        internal_dependencies=metrics.get("internal_dependencies", 0),
        external_dependencies=metrics.get("external_dependencies", 0),
        circular_dependencies=metrics.get("circular_dependencies", 0),
        architecture_hotspots=metrics.get("architecture_hotspots", 0),
        most_connected_modules=metrics.get("most_connected_modules", []),
        most_depended_modules=metrics.get("most_depended_modules", []),
    )


@router.get(
    "/projects/{project_id}/architecture/nodes/{node_id:path}",
    response_model=NodeDetailResponse,
    summary="Get Detailed Node Inspector",
    description="Returns deep metadata for a single node including incoming/outgoing edges, callers, callees, dependencies.",
)
async def get_node_detail(
    project_id: int,
    node_id: str,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    try:
        detail = architecture_service.get_node_detail(project_id, node_id, db)
        return NodeDetailResponse(
            node=GraphNodeSchema.model_validate(detail["node"]),
            incoming_edges=[GraphEdgeSchema.model_validate(e) for e in detail["incoming_edges"]],
            outgoing_edges=[GraphEdgeSchema.model_validate(e) for e in detail["outgoing_edges"]],
            dependencies=[GraphNodeSchema.model_validate(n) for n in detail["dependencies"]],
            dependents=[GraphNodeSchema.model_validate(n) for n in detail["dependents"]],
            metrics=detail["metrics"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching node detail for {node_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
