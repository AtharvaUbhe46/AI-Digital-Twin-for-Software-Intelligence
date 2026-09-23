import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.project import Project
from app.models.digital_twin import DigitalTwin, DigitalTwinSnapshot, DigitalTwinChange, DigitalTwinEvent
from app.services.digital_twin_service import digital_twin_service
from app.services.github_service import GitHubAPIError

client = TestClient(app)


def create_sample_project(db: Session, owner: str = "octocat", repo: str = "Hello-World") -> Project:
    project = Project(
        github_owner=owner,
        github_repo=repo,
        name=repo,
        full_name=f"{owner}/{repo}",
        html_url=f"https://github.com/{owner}/{repo}",
        default_branch="main",
        language="Python",
        stars_count=100,
        forks_count=20,
        is_active=True,
        status="synced",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_digital_twin_initialization():
    """Verify that initialize_twin creates v1 snapshot, twin entity, events, and marks twin ACTIVE."""
    db = SessionLocal()
    try:
        project = create_sample_project(db, "testowner", "testrepo")

        mock_repo_details = {
            "name": "testrepo",
            "description": "Test repository",
            "default_branch": "main",
            "language": "Python",
            "stargazers_count": 100,
            "forks_count": 10,
            "open_issues_count": 2,
        }
        mock_commits = [
            {"sha": "c111", "commit": {"message": "Initial commit", "author": {"name": "Alice", "date": "2026-09-01T12:00:00Z"}}, "author": {"login": "alice"}}
        ]
        mock_contribs = [{"id": 1, "login": "alice", "contributions": 10}]
        mock_issues = [{"id": 101, "number": 1, "title": "First issue", "state": "open", "created_at": "2026-09-01T12:00:00Z"}]
        mock_prs = [{"id": 201, "number": 2, "title": "First PR", "state": "open", "created_at": "2026-09-01T12:00:00Z", "merged_at": None}]

        async def run_init():
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock) as m_meta, \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock) as m_cm, \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock) as m_ct, \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock) as m_is, \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock) as m_pr, \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock) as m_rel, \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock) as m_br, \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock) as m_tr:

                m_meta.return_value = mock_repo_details
                m_cm.return_value = mock_commits
                m_ct.return_value = mock_contribs
                m_is.return_value = mock_issues
                m_pr.return_value = mock_prs
                m_rel.return_value = []
                m_br.return_value = [{"name": "main", "commit": {"sha": "c111"}}]
                m_tr.return_value = [{"path": "README.md", "sha": "blob1", "type": "blob", "size": 100}]

                return await digital_twin_service.initialize_twin(project.id, db)

        res = asyncio.run(run_init())

        assert res["current_version"] == 1
        assert res["status"] == "ACTIVE"

        twin = db.query(DigitalTwin).filter(DigitalTwin.project_id == project.id).first()
        assert twin is not None
        assert twin.current_version == 1
        assert twin.status == "ACTIVE"
        assert twin.fidelity_score > 0

        # Snapshot v1 verification
        snapshots = db.query(DigitalTwinSnapshot).filter(DigitalTwinSnapshot.digital_twin_id == twin.id).all()
        assert len(snapshots) == 1
        assert snapshots[0].version == 1
        assert snapshots[0].entity_counts["commits"] == 1

        # Event verification
        events = db.query(DigitalTwinEvent).filter(DigitalTwinEvent.digital_twin_id == twin.id).all()
        event_types = [e.event_type for e in events]
        assert "TWIN_INITIALIZED" in event_types
        assert "TWIN_SYNCHRONIZED" in event_types

    finally:
        db.close()


def test_synchronize_with_changes_and_idempotency():
    """Verify that sync detects changes, increments version to v2, and a consecutive sync is idempotent."""
    db = SessionLocal()
    try:
        project = create_sample_project(db, "testowner", "testsync")

        # Initial baseline state
        mock_meta = {"name": "testsync", "default_branch": "main", "stargazers_count": 50}
        mock_commits_v1 = [
            {"sha": "c111", "commit": {"message": "Initial commit", "author": {"name": "Alice"}}, "author": {"login": "alice"}}
        ]
        mock_issues_v1 = [{"id": 101, "number": 1, "title": "Open issue", "state": "open"}]

        async def run_scenario():
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock, return_value=mock_meta), \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock, return_value=mock_commits_v1), \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock, return_value=[{"login": "alice", "contributions": 1}]), \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock, return_value=mock_issues_v1), \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock, return_value=[{"name": "main"}]), \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock, return_value=[]):
                await digital_twin_service.initialize_twin(project.id, db)

            # Sync 2: Adds a new commit and closes issue #1 -> should trigger v2
            mock_commits_v2 = [
                {"sha": "c222", "commit": {"message": "Feature addition", "author": {"name": "Bob"}}, "author": {"login": "bob"}},
                {"sha": "c111", "commit": {"message": "Initial commit", "author": {"name": "Alice"}}, "author": {"login": "alice"}},
            ]
            mock_issues_v2 = [{"id": 101, "number": 1, "title": "Open issue", "state": "closed", "closed_at": "2026-09-02T10:00:00Z"}]
            mock_contribs_v2 = [
                {"login": "alice", "contributions": 1},
                {"login": "bob", "contributions": 1},
            ]

            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock, return_value=mock_meta), \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock, return_value=mock_commits_v2), \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock, return_value=mock_contribs_v2), \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock, return_value=mock_issues_v2), \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock, return_value=[{"name": "main"}]), \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock, return_value=[]):
                res_v2 = await digital_twin_service.synchronize_twin(project.id, db)

            # Sync 3 (Immediate Idempotency Test): No new repository changes
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock, return_value=mock_meta), \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock, return_value=mock_commits_v2), \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock, return_value=mock_contribs_v2), \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock, return_value=mock_issues_v2), \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock, return_value=[{"name": "main"}]), \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock, return_value=[]):
                res_v3 = await digital_twin_service.synchronize_twin(project.id, db)

            return res_v2, res_v3

        res_v2, res_v3 = asyncio.run(run_scenario())

        assert res_v2["previous_version"] == 1
        assert res_v2["current_version"] == 2
        assert res_v2["changes_detected"] >= 2

        # Verify changes were saved
        twin = db.query(DigitalTwin).filter(DigitalTwin.project_id == project.id).first()
        changes = db.query(DigitalTwinChange).filter(DigitalTwinChange.digital_twin_id == twin.id).all()
        change_types = [c.change_type for c in changes]
        assert "CREATED" in change_types
        assert "STATE_CHANGED" in change_types

        # Idempotency assertions
        assert res_v3["current_version"] == 2
        assert res_v3["changes_detected"] == 0
        assert "No repository changes detected" in res_v3["message"]

        # Snapshot count should remain 2
        snapshots = db.query(DigitalTwinSnapshot).filter(DigitalTwinSnapshot.digital_twin_id == twin.id).all()
        assert len(snapshots) == 2

    finally:
        db.close()


def test_repository_isolation():
    """Verify that Project A and Project B have distinct and isolated Digital Twins."""
    db = SessionLocal()
    try:
        proj_a = create_sample_project(db, "facebook", "react")
        proj_b = create_sample_project(db, "vuejs", "vue")

        mock_meta_a = {"name": "react", "default_branch": "main"}
        mock_meta_b = {"name": "vue", "default_branch": "main"}

        async def run_isolation():
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock) as m_meta, \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock, return_value=[]):

                m_meta.return_value = mock_meta_a
                await digital_twin_service.initialize_twin(proj_a.id, db)

                m_meta.return_value = mock_meta_b
                await digital_twin_service.initialize_twin(proj_b.id, db)

        asyncio.run(run_isolation())

        twin_a = digital_twin_service.get_or_create_twin(proj_a.id, db)
        twin_b = digital_twin_service.get_or_create_twin(proj_b.id, db)

        assert twin_a.id != twin_b.id
        assert twin_a.project_id == proj_a.id
        assert twin_b.project_id == proj_b.id

        # Verify state query isolation
        state_a = digital_twin_service.get_current_state(proj_a.id, db)
        state_b = digital_twin_service.get_current_state(proj_b.id, db)

        assert state_a["repository"]["full_name"] == "facebook/react"
        assert state_b["repository"]["full_name"] == "vuejs/vue"

    finally:
        db.close()


def test_failure_handling_and_preservation():
    """Verify that a GitHub API failure sets twin status to ERROR and leaves previous snapshot intact."""
    db = SessionLocal()
    try:
        project = create_sample_project(db, "errororg", "errorrepo")

        # Initial successful sync
        mock_meta = {"name": "errorrepo", "default_branch": "main"}

        async def run_failure():
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock, return_value=mock_meta), \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock, return_value=[]):
                await digital_twin_service.initialize_twin(project.id, db)

            twin = digital_twin_service.get_or_create_twin(project.id, db)
            assert twin.status == "ACTIVE"
            assert twin.current_version == 1

            # Simulate GitHub failure on second sync
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock, side_effect=GitHubAPIError("GitHub API Down", 502)):
                with pytest.raises(GitHubAPIError):
                    await digital_twin_service.synchronize_twin(project.id, db)

        asyncio.run(run_failure())

        twin = digital_twin_service.get_or_create_twin(project.id, db)
        assert twin.status == "ERROR"
        assert "GitHub API Down" in twin.error_message
        assert twin.current_version == 1

        # Previous snapshot v1 remains intact
        snapshots = db.query(DigitalTwinSnapshot).filter(DigitalTwinSnapshot.digital_twin_id == twin.id).all()
        assert len(snapshots) == 1
        assert snapshots[0].version == 1

    finally:
        db.close()


def test_snapshot_comparison():
    """Verify that compare_snapshots correctly compares v1 vs v2 diffs."""
    db = SessionLocal()
    try:
        project = create_sample_project(db, "comparer", "diffrepo")

        # Snapshot 1
        mock_meta = {"name": "diffrepo", "default_branch": "main"}
        mock_commits_v1 = [{"sha": "c111", "commit": {"message": "c1", "author": {"name": "A"}}}]

        # Snapshot 2 (adds commit c222)
        mock_commits_v2 = [
            {"sha": "c222", "commit": {"message": "c2", "author": {"name": "B"}}},
            {"sha": "c111", "commit": {"message": "c1", "author": {"name": "A"}}},
        ]

        async def run_comp():
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock, return_value=mock_meta), \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock, return_value=mock_commits_v1), \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock, return_value=[]):
                await digital_twin_service.initialize_twin(project.id, db)

            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock, return_value=mock_meta), \
                 patch("app.services.digital_twin_service.github_service.get_commits", new_callable=AsyncMock, return_value=mock_commits_v2), \
                 patch("app.services.digital_twin_service.github_service.get_contributors", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_issues", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_pull_requests", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_releases", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_branches", new_callable=AsyncMock, return_value=[]), \
                 patch("app.services.digital_twin_service.github_service.get_repo_tree", new_callable=AsyncMock, return_value=[]):
                await digital_twin_service.synchronize_twin(project.id, db)

        asyncio.run(run_comp())

        # Run comparison between v1 and v2
        diff = digital_twin_service.compare_snapshots(project.id, v_from=1, v_to=2, db=db)
        assert diff["v_from"] == 1
        assert diff["v_to"] == 2
        assert len(diff["added"]) >= 1
        assert diff["summary"]["version_span"] == "v1 → v2"

    finally:
        db.close()


def test_digital_twin_api_endpoints():
    """Verify FastAPI endpoints for Digital Twin Core."""
    db = SessionLocal()
    try:
        project = create_sample_project(db, "apitest", "apitwin")

        # 1. GET /projects/{id}/digital-twin
        res = client.get(f"/api/v1/projects/{project.id}/digital-twin")
        assert res.status_code == 200
        data = res.json()
        assert data["project_id"] == project.id
        assert data["current_version"] == 1
        assert data["status"] in ("NOT_INITIALIZED", "ACTIVE")

        # 2. GET /projects/{id}/digital-twin/state
        res_state = client.get(f"/api/v1/projects/{project.id}/digital-twin/state")
        assert res_state.status_code == 200
        state = res_state.json()
        assert "twin" in state
        assert "entity_counts" in state
        assert "repository" in state

        # 3. GET /projects/{id}/digital-twin/entities
        res_ent = client.get(f"/api/v1/projects/{project.id}/digital-twin/entities")
        assert res_ent.status_code == 200
        assert "total_entities" in res_ent.json()

        # 4. GET /projects/{id}/digital-twin/snapshots
        res_snaps = client.get(f"/api/v1/projects/{project.id}/digital-twin/snapshots")
        assert res_snaps.status_code == 200
        assert isinstance(res_snaps.json(), list)

    finally:
        db.close()
