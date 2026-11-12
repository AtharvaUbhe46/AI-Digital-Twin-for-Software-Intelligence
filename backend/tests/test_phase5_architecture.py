import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.project import Project
from app.services.architecture.parser.python_parser import PythonASTParser
from app.services.architecture.parser.js_ts_parser import JSTypeScriptParser
from app.services.architecture.parser.manifest_parser import ManifestParser
from app.services.architecture.parser import parser_engine, ParsedEntity, ParsedRelation
from app.services.architecture.graph.cycle_detector import CycleDetector
from app.services.architecture.graph.graph_builder import KnowledgeGraphBuilder
from app.services.architecture.graph.architecture_engine import ArchitectureEngine
from app.services.architecture.architecture_service import architecture_service

client = TestClient(app)


# ─── 1. Parser Tests ──────────────────────────────────────────────────────────

def test_python_ast_parser_classes_functions_routes():
    parser = PythonASTParser()
    code = '''
from fastapi import APIRouter
from app.models.base import Base

router = APIRouter()
MAX_LIMIT = 100

class ServiceEngine(Base):
    """Engine service docstring."""
    def __init__(self, name: str):
        self.name = name

    def compute(self, x: int) -> int:
        return x * 2

@router.get("/items/{item_id}")
async def get_item(item_id: int):
    engine = ServiceEngine("test")
    return {"result": engine.compute(item_id)}
'''
    entities, relations = parser.parse_file("app/api/v1/endpoints/items.py", code)

    # Validate Entities
    types = {e.entity_type for e in entities}
    assert "file" in types
    assert "class" in types
    assert "function" in types
    assert "method" in types
    assert "api_endpoint" in types
    assert "variable" in types

    # Class details
    class_ent = next(e for e in entities if e.name == "ServiceEngine")
    assert class_ent.metadata["bases"] == ["Base"]

    # Endpoint details
    endpoint_ent = next(e for e in entities if e.entity_type == "api_endpoint")
    assert endpoint_ent.name == "GET /items/{item_id}"
    assert endpoint_ent.metadata["http_method"] == "GET"

    # Relations
    rel_types = {r.rel_type for r in relations}
    assert "CONTAINS" in rel_types
    assert "ROUTES_TO" in rel_types
    assert "IMPORTS" in rel_types
    assert "EXTENDS" in rel_types


def test_js_ts_parser_imports_exports():
    parser = JSTypeScriptParser()
    code = '''
import React, { useState } from 'react';
import axios from 'axios';
import { StatCard } from './components/StatCard';

export interface DashboardProps {
    title: string;
}

export const DashboardView: React.FC<DashboardProps> = ({ title }) => {
    const [data, setData] = useState(null);
    return <StatCard title={title} />;
};

export default DashboardView;
'''
    entities, relations = parser.parse_file("src/pages/DashboardView.tsx", code)

    names = {e.name for e in entities}
    assert "DashboardView.tsx" in names
    assert "DashboardView" in names
    assert "DashboardProps" in names

    rel_types = {r.rel_type for r in relations}
    assert "IMPORTS" in rel_types
    assert "CONTAINS" in rel_types
    assert "EXPORTS" in rel_types


def test_manifest_parser_package_json_and_requirements():
    parser = ManifestParser()

    # package.json
    pkg_json = '''{
        "dependencies": {
            "react": "^18.3.1",
            "axios": "^1.7.2"
        },
        "devDependencies": {
            "typescript": "^5.4.5"
        }
    }'''
    entities, relations = parser.parse_file("package.json", pkg_json)
    names = {e.name for e in entities}
    assert "react" in names
    assert "axios" in names
    assert "typescript" in names
    assert all(r.rel_type == "DEPENDS_ON" for r in relations)

    # requirements.txt
    req_txt = '''
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
# Comment line
pytest>=8.0.0
'''
    req_entities, req_relations = parser.parse_file("requirements.txt", req_txt)
    req_names = {e.name for e in req_entities}
    assert "fastapi" in req_names
    assert "uvicorn" in req_names
    assert "pytest" in req_names


# ─── 2. Cycle Detection Tests ─────────────────────────────────────────────────

def test_cycle_detector_cyclic_fixture():
    # 3-node cycle: A -> B -> C -> A
    adjacency = {
        "file:A.py": {"file:B.py"},
        "file:B.py": {"file:C.py"},
        "file:C.py": {"file:A.py"},
    }
    cycles = CycleDetector.detect_cycles(adjacency)
    assert len(cycles) == 1
    c = cycles[0]
    assert c["length"] == 3
    assert set(c["nodes"]) == {"file:A.py", "file:B.py", "file:C.py"}
    assert c["path"][0] == c["path"][-1]  # Closed loop


def test_cycle_detector_direct_circular_dependency():
    # 2-node direct cycle: A -> B -> A
    adjacency = {
        "file:A.py": {"file:B.py"},
        "file:B.py": {"file:A.py"},
    }
    cycles = CycleDetector.detect_cycles(adjacency)
    assert len(cycles) == 1
    assert cycles[0]["length"] == 2
    assert cycles[0]["severity"] == "CRITICAL"


def test_cycle_detector_acyclic_fixture():
    # Acyclic graph: A -> B -> C
    adjacency = {
        "file:A.py": {"file:B.py"},
        "file:B.py": {"file:C.py"},
        "file:C.py": set(),
    }
    cycles = CycleDetector.detect_cycles(adjacency)
    assert len(cycles) == 0


# ─── 3. Knowledge Graph Builder & Architecture Metrics ────────────────────────

def test_knowledge_graph_builder_and_coupling_metrics():
    entities = [
        ParsedEntity(id="file:app/core/db.py", name="db.py", entity_type="file", file_path="app/core/db.py", module="app.core"),
        ParsedEntity(id="file:app/services/user.py", name="user.py", entity_type="file", file_path="app/services/user.py", module="app.services"),
        ParsedEntity(id="file:app/api/user.py", name="user.py", entity_type="file", file_path="app/api/user.py", module="app.api"),
        ParsedEntity(id="pkg:fastapi", name="fastapi", entity_type="package", file_path="requirements.txt", module="external", metadata={"version": "0.110.0"}),
    ]
    relations = [
        ParsedRelation(source_id="file:app/services/user.py", target_id="file:app/core/db.py", rel_type="IMPORTS"),
        ParsedRelation(source_id="file:app/api/user.py", target_id="file:app/services/user.py", rel_type="IMPORTS"),
        ParsedRelation(source_id="file:app/api/user.py", target_id="pkg:fastapi", rel_type="DEPENDS_ON"),
    ]

    nodes, edges = KnowledgeGraphBuilder.build_graph(entities, relations, project_id=1)
    assert len(nodes) >= 4
    assert len(edges) == 3

    arch_result = ArchitectureEngine.analyze_architecture(nodes, edges)
    modules = {m["module"]: m for m in arch_result["modules"]}

    # app.core has 1 incoming (Ca=1), 0 outgoing (Ce=0) -> Instability = 0.0 (completely stable)
    if "app.core" in modules:
        assert modules["app.core"]["afferent_coupling"] >= 1
        assert modules["app.core"]["efferent_coupling"] == 0
        assert modules["app.core"]["instability"] == 0.0

    # app.api has 0 incoming (Ca=0), 1 outgoing (Ce=1) -> Instability = 1.0 (completely unstable)
    if "app.api" in modules:
        assert modules["app.api"]["efferent_coupling"] >= 1
        assert modules["app.api"]["instability"] == 1.0


# ─── 4. End-to-End API Endpoints Tests ────────────────────────────────────────

def test_architecture_api_endpoints():
    from app.schemas.architecture import AnalyzeRequest
    from app.api.v1.endpoints.architecture import (
        analyze_project_architecture,
        get_architecture_status,
        get_knowledge_graph,
        get_architecture_overview,
        get_dependencies_analysis,
        get_circular_dependencies,
        get_architecture_metrics,
        get_node_detail,
        get_endpoint_changes,
    )

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.full_name == "test/digital-twin").first()
        if not project:
            project = Project(
                github_owner="test",
                github_repo="digital-twin",
                name="digital-twin",
                full_name="test/digital-twin",
                html_url="https://github.com/test/digital-twin",
                is_active=True,
                status="synced"
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        p_id = project.id

        # 1. Trigger Analysis
        analysis_resp = analyze_project_architecture(p_id, AnalyzeRequest(force_refresh=False), db)
        assert analysis_resp.status == "COMPLETED"

        # 2. Get Status
        status_resp = get_architecture_status(p_id, db)
        assert status_resp.status == "COMPLETED"

        # 3. Get Knowledge Graph
        graph_data = get_knowledge_graph(p_id, None, None, None, None, 50, db)
        assert len(graph_data.nodes) > 0
        assert len(graph_data.edges) > 0
        assert graph_data.total_nodes > 0

        # 4. Get Overview
        overview_data = get_architecture_overview(p_id, db)
        assert overview_data.total_files > 0
        assert isinstance(overview_data.modules, list)

        # 5. Get Dependencies
        deps_data = get_dependencies_analysis(p_id, db)
        assert deps_data.total_packages >= 0
        assert isinstance(deps_data.packages, list)

        # 6. Get Cycles
        cycles_data = get_circular_dependencies(p_id, db)
        assert isinstance(cycles_data.cycles, list)

        # 7. Get Metrics
        metrics_data = get_architecture_metrics(p_id, db)
        assert metrics_data.total_files > 0

        # 8. Get Node Detail
        if graph_data.nodes:
            first_node_id = graph_data.nodes[0].id
            node_resp = get_node_detail(p_id, first_node_id, db)
            assert node_resp.node.id == first_node_id

        # 9. Get Endpoint Changes & Impact Analysis
        ep_data = get_endpoint_changes(p_id, db)
        assert "added" in ep_data
        assert "removed" in ep_data
        assert "modified" in ep_data
        assert "impact_analysis" in ep_data
    finally:
        db.close()
