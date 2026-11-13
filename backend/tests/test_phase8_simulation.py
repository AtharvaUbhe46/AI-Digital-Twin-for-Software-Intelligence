from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal, init_db
from app.models.project import Project, Contributor, Commit, Issue, PullRequest, Release
from app.models.digital_twin import DigitalTwin, DigitalTwinSnapshot
from app.models.simulation import WhatIfSimulation
from app.schemas.simulation import SimulationCreateRequest, SimulationParameterInput
from app.services.simulation_service import simulation_engine

client = TestClient(app)


def create_sample_project(db: Session, owner: str = "sim-org", repo: str = "sim-repo") -> Project:
    project = Project(
        github_owner=owner,
        github_repo=repo,
        name=repo,
        full_name=f"{owner}/{repo}",
        html_url=f"https://github.com/{owner}/{repo}",
        default_branch="main",
        language="TypeScript",
        stars_count=120,
        forks_count=25,
        open_issues_count=10,
        open_prs_count=4,
        is_active=True,
        status="synced",
        health_score=72.5,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Add contributors
    for i in range(1, 6):
        db.add(Contributor(
            project_id=project.id,
            login=f"dev{i}",
            contributions=50 if i == 1 else 10,
        ))

    # Add commits
    now = datetime.now(timezone.utc)
    for i in range(15):
        db.add(Commit(
            project_id=project.id,
            sha=f"commit_{i:04d}",
            message=f"Feat {i}",
            author_login=f"dev{(i % 5) + 1}",
            author_date=now - timedelta(days=i),
        ))

    # Add issues
    for i in range(1, 11):
        db.add(Issue(
            project_id=project.id,
            number=i,
            title=f"Bug {i}",
            state="open" if i <= 7 else "closed",
            created_at=now - timedelta(days=i * 5),
        ))

    # Add PRs
    for i in range(1, 5):
        db.add(PullRequest(
            project_id=project.id,
            number=i + 100,
            title=f"PR {i}",
            state="open" if i <= 3 else "closed",
            is_merged=False if i <= 3 else True,
            created_at=now - timedelta(days=i * 2),
        ))

    # Add Digital Twin Core record
    twin = DigitalTwin(
        project_id=project.id,
        current_version=2,
        status="ACTIVE",
        fidelity_score=95.0,
    )
    db.add(twin)
    db.commit()
    db.refresh(twin)

    # Add snapshot
    snap = DigitalTwinSnapshot(
        digital_twin_id=twin.id,
        version=2,
        source="github_sync",
        summary="Baseline snapshot",
        entity_counts={"contributors": 5, "commits": 15, "issues": 10, "prs": 4},
    )
    db.add(snap)
    db.commit()

    return project


def test_simulation_baseline_retrieval():
    """Verify baseline returns real project telemetry and metadata."""
    init_db()
    db = SessionLocal()
    try:
        project = create_sample_project(db, "org-base", "repo-base")
        baseline = simulation_engine.get_baseline(project.id, db)

        assert baseline.project_id == project.id
        assert baseline.project_name == "repo-base"
        assert baseline.twin_version == 2
        assert baseline.metrics["total_contributors"] == 5
        assert baseline.metrics["open_issues"] == 7
        assert len(baseline.available_parameters) >= 5
    finally:
        db.close()


def test_team_expansion_simulation_brooks_law():
    """Verify that adding active contributors calculates coordination overhead and scales health."""
    init_db()
    db = SessionLocal()
    try:
        project = create_sample_project(db, "org-team", "repo-team")
        initial_open_issues = project.open_issues_count

        request = SimulationCreateRequest(
            name="Scale Engineering Team",
            description="Testing impact of adding 4 active developers",
            category="team",
            parameters=[
                SimulationParameterInput(
                    parameter_key="active_contributors",
                    proposed_value=9.0,
                    user_notes="Hiring 4 additional maintainers",
                )
            ]
        )

        result = simulation_engine.simulate(project.id, request, db, persist=True)

        assert result.status == "COMPLETED"
        assert result.simulated_metrics["active_contributors"] == 9
        # Check Brooks' law coordination overhead was computed
        assert "coordination_overhead_factor" in result.simulated_metrics
        assert result.simulated_metrics["coordination_overhead_factor"] > 1.0
        assert len(result.impact_analysis) >= 1
        assert len(result.opportunities) >= 1

        # Verify real database repository remains completely unchanged!
        refreshed_project = db.query(Project).filter(Project.id == project.id).first()
        assert refreshed_project.open_issues_count == initial_open_issues
        assert len(refreshed_project.contributors) == 5
    finally:
        db.close()


def test_issue_backlog_reduction_simulation():
    """Verify that resolving open issues reduces backlog and improves health score."""
    init_db()
    db = SessionLocal()
    try:
        project = create_sample_project(db, "org-issues", "repo-issues")

        request = SimulationCreateRequest(
            name="Sprint Triage Backlog",
            description="Clear 5 open issues",
            category="issues",
            parameters=[
                SimulationParameterInput(
                    parameter_key="open_issues",
                    proposed_value=2.0,
                    user_notes="Targeting zero stale bugs",
                )
            ]
        )

        result = simulation_engine.simulate(project.id, request, db, persist=True)

        assert result.status == "COMPLETED"
        assert result.simulated_metrics["open_issues"] == 2
        # Health impact must show improvement
        assert result.health_impact.delta is not None
        assert result.health_impact.delta >= 0
        assert len(result.opportunities) >= 1
    finally:
        db.close()


def test_multi_parameter_custom_scenario():
    """Verify that multi-parameter scenarios combine team, issues, and activity correctly."""
    init_db()
    db = SessionLocal()
    try:
        project = create_sample_project(db, "org-custom", "repo-custom")

        request = SimulationCreateRequest(
            name="Comprehensive Transformation",
            description="Add developers, clear issues, and double shipping cadence",
            category="custom",
            parameters=[
                SimulationParameterInput(parameter_key="active_contributors", proposed_value=8.0),
                SimulationParameterInput(parameter_key="open_issues", proposed_value=3.0),
                SimulationParameterInput(parameter_key="commits_per_week", proposed_value=12.0),
            ]
        )

        result = simulation_engine.simulate(project.id, request, db, persist=True)

        assert len(result.parameters) == 3
        assert result.simulated_metrics["active_contributors"] == 8
        assert result.simulated_metrics["open_issues"] == 3
        assert result.simulated_metrics["commits_per_week"] == 12.0
        assert result.health_impact.simulated_score is not None
        assert result.ai_explanation.summary != ""
    finally:
        db.close()


def test_simulation_persistence_and_deletion():
    """Verify saved simulations can be listed, fetched, and deleted without touching real project."""
    init_db()
    db = SessionLocal()
    try:
        project = create_sample_project(db, "org-persist", "repo-persist")

        request = SimulationCreateRequest(
            name="Test Persistence",
            category="team",
            parameters=[SimulationParameterInput(parameter_key="active_contributors", proposed_value=7.0)]
        )

        created = simulation_engine.simulate(project.id, request, db, persist=True)
        assert created.id > 0

        # List simulations
        history = simulation_engine.get_simulations(project.id, db)
        assert any(s.id == created.id for s in history)

        # Get details
        detail = simulation_engine.get_simulation_detail(project.id, created.id, db)
        assert detail.id == created.id

        # Delete simulation
        deleted = simulation_engine.delete_simulation(project.id, created.id, db)
        assert deleted is True

        # Ensure project is still intact
        proj = db.query(Project).filter(Project.id == project.id).first()
        assert proj is not None
    finally:
        db.close()


def test_simulation_comparison():
    """Verify comparison between two different saved scenarios."""
    init_db()
    db = SessionLocal()
    try:
        project = create_sample_project(db, "org-compare", "repo-compare")

        # Scenario A: scale contributors
        req_a = SimulationCreateRequest(
            name="Scenario A - Scale Team",
            category="team",
            parameters=[SimulationParameterInput(parameter_key="active_contributors", proposed_value=10.0)]
        )
        sim_a = simulation_engine.simulate(project.id, req_a, db, persist=True)

        # Scenario B: focus on issue resolution
        req_b = SimulationCreateRequest(
            name="Scenario B - Triage Backlog",
            category="issues",
            parameters=[SimulationParameterInput(parameter_key="open_issues", proposed_value=1.0)]
        )
        sim_b = simulation_engine.simulate(project.id, req_b, db, persist=True)

        comp = simulation_engine.compare_simulations(project.id, sim_a.id, sim_b.id, db)

        assert comp.simulation_a.id == sim_a.id
        assert comp.simulation_b.id == sim_b.id
        assert len(comp.parameter_differences) >= 1
        assert len(comp.metric_comparisons) >= 4
        assert "health_score_advantage" in comp.health_comparison
        assert comp.comparative_summary != ""
    finally:
        db.close()


def test_simulation_api_endpoints():
    """Verify FastAPI REST endpoints for What-If Simulation."""
    init_db()
    db = SessionLocal()
    try:
        project = create_sample_project(db, "org-api", "repo-api")
        pid = project.id

        # 1. Baseline endpoint
        resp_base = client.get(f"/api/v1/projects/{pid}/simulations/baseline")
        assert resp_base.status_code == 200
        assert resp_base.json()["project_id"] == pid

        # 2. Create simulation endpoint
        payload = {
            "name": "API Test Scenario",
            "description": "Via REST API",
            "category": "team",
            "parameters": [
                {"parameter_key": "active_contributors", "proposed_value": 8.0, "user_notes": "API test"}
            ]
        }
        resp_post = client.post(f"/api/v1/projects/{pid}/simulations", json=payload)
        assert resp_post.status_code == 201
        sim_data = resp_post.json()
        sim_id = sim_data["id"]
        assert sim_data["name"] == "API Test Scenario"

        # 3. List simulations endpoint
        resp_list = client.get(f"/api/v1/projects/{pid}/simulations")
        assert resp_list.status_code == 200
        assert len(resp_list.json()) >= 1

        # 4. Detail endpoint
        resp_detail = client.get(f"/api/v1/projects/{pid}/simulations/{sim_id}")
        assert resp_detail.status_code == 200
        assert resp_detail.json()["id"] == sim_id

        # 5. Delete endpoint
        resp_del = client.delete(f"/api/v1/projects/{pid}/simulations/{sim_id}")
        assert resp_del.status_code == 200
    finally:
        db.close()

