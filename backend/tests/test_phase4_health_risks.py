import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.project import Project, Commit, Issue, PullRequest, Release, Contributor
from app.models.digital_twin import DigitalTwin
from app.models.health import SoftwareHealthSnapshot, HealthDimensionResult
from app.models.risk import SoftwareRisk
from app.services.health.health_service import health_service
from app.services.risk.risk_service import risk_service
from app.services.digital_twin_service import digital_twin_service
from app.core.config import settings

client = TestClient(app)


def create_test_project(db: Session, owner: str = "org", repo: str = "repo") -> Project:
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


# 1. Health calculation with normal repository data
def test_health_calculation_normal_repository_data():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "normal", "repo")
        now = datetime.now(timezone.utc)

        # Commits (recent and regular)
        for i in range(10):
            db.add(Commit(
                project_id=proj.id,
                sha=f"sha{i:04d}",
                message=f"Commit {i}",
                author_name=f"Author {i % 3}",
                author_login=f"dev{i % 3}",
                author_date=now - timedelta(days=i),
            ))

        # Issues (clean, recent)
        db.add(Issue(project_id=proj.id, number=1, title="Issue 1", state="closed", created_at=now - timedelta(days=5), closed_at=now - timedelta(days=1)))
        db.add(Issue(project_id=proj.id, number=2, title="Issue 2", state="open", created_at=now - timedelta(days=2)))

        # PRs (merged recently)
        db.add(PullRequest(project_id=proj.id, number=10, title="PR 10", state="closed", is_merged=True, created_at=now - timedelta(days=4), merged_at=now - timedelta(days=2)))

        # Release (recent)
        db.add(Release(project_id=proj.id, tag_name="v1.0.0", name="v1.0.0", published_at=now - timedelta(days=10)))
        db.commit()

        snapshot = health_service.calculate_and_persist_health(proj.id, db)
        assert snapshot.overall_score >= 70.0
        assert snapshot.overall_status in ("HEALTHY", "ATTENTION")
        assert len(snapshot.dimensions) == 6
    finally:
        db.close()


# 2. Health calculation with no issues
def test_health_calculation_no_issues():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "no-issues", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))
        db.commit()

        snapshot = health_service.calculate_and_persist_health(proj.id, db)
        issue_dim = next((d for d in snapshot.dimensions if d.dimension == "issues"), None)
        assert issue_dim is not None
        assert issue_dim.status == "INSUFFICIENT_DATA"
    finally:
        db.close()


# 3. Health calculation with many stale issues
def test_health_calculation_many_stale_issues():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "stale-issues", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))

        # 6 stale issues older than 30 days
        for i in range(6):
            db.add(Issue(
                project_id=proj.id,
                number=i + 1,
                title=f"Old Issue {i}",
                state="open",
                created_at=now - timedelta(days=45 + i),
            ))
        db.commit()

        snapshot = health_service.calculate_and_persist_health(proj.id, db)
        issue_dim = next((d for d in snapshot.dimensions if d.dimension == "issues"), None)
        assert issue_dim is not None
        assert issue_dim.status in ("DEGRADED", "CRITICAL")
        assert issue_dim.score < 50.0
    finally:
        db.close()


# 4. Health calculation with stale PRs
def test_health_calculation_stale_prs():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "stale-prs", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))

        # PR older than 14 days
        db.add(PullRequest(
            project_id=proj.id,
            number=101,
            title="Abandoned PR",
            state="open",
            created_at=now - timedelta(days=25),
        ))
        db.commit()

        snapshot = health_service.calculate_and_persist_health(proj.id, db)
        pr_dim = next((d for d in snapshot.dimensions if d.dimension == "pull_requests"), None)
        assert pr_dim is not None
        assert pr_dim.score < 70.0
        assert pr_dim.metrics["stale_count"] == 1
    finally:
        db.close()


# 5. Insufficient release data handling
def test_insufficient_release_data():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "no-releases", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))
        db.commit()

        snapshot = health_service.calculate_and_persist_health(proj.id, db)
        rel_dim = next((d for d in snapshot.dimensions if d.dimension == "releases"), None)
        assert rel_dim is not None
        assert rel_dim.status == "INSUFFICIENT_DATA"
        assert rel_dim.score is None
        # Overall score still calculated from remaining available dimensions
        assert snapshot.overall_score > 0.0
    finally:
        db.close()


# 6. Repository inactivity risk trigger
def test_risk_repository_inactivity():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "inactive", "repo")
        now = datetime.now(timezone.utc)
        # Commit pushed 25 days ago (threshold is 14 days)
        db.add(Commit(project_id=proj.id, sha="c001", message="Old", author_name="Dev", author_date=now - timedelta(days=25)))
        db.commit()

        risks = risk_service.evaluate_and_persist_risks(proj.id, db)
        inact_risk = next((r for r in risks if r.risk_type == "REPOSITORY_INACTIVITY"), None)
        assert inact_risk is not None
        assert inact_risk.severity == "MEDIUM"
        assert inact_risk.status == "OPEN"
        assert "25 days" in inact_risk.metric_value
    finally:
        db.close()


# 7. Stale issue risk trigger
def test_risk_stale_issues():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "stale-issue-risk", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))
        db.add(Issue(project_id=proj.id, number=42, title="Bug 42", state="open", created_at=now - timedelta(days=35)))
        db.commit()

        risks = risk_service.evaluate_and_persist_risks(proj.id, db)
        stale_risk = next((r for r in risks if r.risk_type == "STALE_ISSUES"), None)
        assert stale_risk is not None
        assert stale_risk.status == "OPEN"
        assert len(stale_risk.affected_entities) == 1
        assert stale_risk.affected_entities[0]["number"] == 42
    finally:
        db.close()


# 8. Stale PR risk trigger
def test_risk_stale_pull_requests():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "stale-pr-risk", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))
        db.add(PullRequest(project_id=proj.id, number=99, title="Unreviewed Feature", state="open", created_at=now - timedelta(days=20)))
        db.commit()

        risks = risk_service.evaluate_and_persist_risks(proj.id, db)
        pr_risk = next((r for r in risks if r.risk_type == "STALE_PULL_REQUESTS"), None)
        assert pr_risk is not None
        assert pr_risk.status == "OPEN"
        assert pr_risk.affected_entities[0]["number"] == 99
    finally:
        db.close()


# 9. Issue backlog growth risk trigger
def test_risk_issue_backlog_growth():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "backlog-growth", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))

        # 7 issues created in the last 10 days, 0 closed (threshold net is 5)
        for i in range(7):
            db.add(Issue(project_id=proj.id, number=i + 1, title=f"Issue {i}", state="open", created_at=now - timedelta(days=5)))
        db.commit()

        risks = risk_service.evaluate_and_persist_risks(proj.id, db)
        bg_risk = next((r for r in risks if r.risk_type == "ISSUE_BACKLOG_GROWTH"), None)
        assert bg_risk is not None
        assert "+7 net issues" in bg_risk.metric_value
    finally:
        db.close()


# 10. PR backlog growth risk trigger
def test_risk_pr_backlog_growth():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "pr-backlog-growth", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=1)))

        # 4 PRs opened in recent period, 0 merged (threshold is 3)
        for i in range(4):
            db.add(PullRequest(project_id=proj.id, number=200 + i, title=f"PR {i}", state="open", created_at=now - timedelta(days=3)))
        db.commit()

        risks = risk_service.evaluate_and_persist_risks(proj.id, db)
        pr_bg = next((r for r in risks if r.risk_type == "PR_BACKLOG_GROWTH"), None)
        assert pr_bg is not None
        assert "+4 net PRs" in pr_bg.metric_value
    finally:
        db.close()


# 11. Contributor concentration risk trigger
def test_risk_contributor_concentration():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "concentration", "repo")
        now = datetime.now(timezone.utc)

        # 9 commits by dev1, 1 commit by dev2 (90% concentration > 65% threshold)
        for i in range(9):
            db.add(Commit(project_id=proj.id, sha=f"c10{i}", message=f"Commit {i}", author_login="dev1", author_date=now - timedelta(days=i)))
        db.add(Commit(project_id=proj.id, sha="c109", message="Commit 9", author_login="dev2", author_date=now - timedelta(days=1)))
        db.commit()

        risks = risk_service.evaluate_and_persist_risks(proj.id, db)
        conc_risk = next((r for r in risks if r.risk_type == "LOW_CONTRIBUTOR_DIVERSITY"), None)
        assert conc_risk is not None
        assert "90.0%" in conc_risk.metric_value
        assert conc_risk.evidence["top_contributor"] == "dev1"
    finally:
        db.close()


# 12. Risk deduplication on repeated sync
def test_risk_deduplication():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "dedup", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=25)))
        db.commit()

        risks_pass1 = risk_service.evaluate_and_persist_risks(proj.id, db)
        initial_count = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == proj.id).count()

        # Re-evaluate
        risks_pass2 = risk_service.evaluate_and_persist_risks(proj.id, db)
        final_count = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == proj.id).count()

        assert initial_count == final_count
        assert len(risks_pass1) == len(risks_pass2)
    finally:
        db.close()


# 13. Risk auto-resolution when condition disappears
def test_risk_auto_resolution():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "autoresolve", "repo")
        now = datetime.now(timezone.utc)
        commit = Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=25))
        db.add(commit)
        db.commit()

        risk_service.evaluate_and_persist_risks(proj.id, db)
        risk = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == proj.id, SoftwareRisk.risk_type == "REPOSITORY_INACTIVITY").first()
        assert risk.status == "OPEN"

        # Now push a new commit today (condition resolved)
        db.add(Commit(project_id=proj.id, sha="c002", message="Fresh commit", author_name="Dev", author_date=now))
        db.commit()

        risk_service.evaluate_and_persist_risks(proj.id, db)
        db.refresh(risk)
        assert risk.status == "RESOLVED"
        assert risk.resolved_at is not None
    finally:
        db.close()


# 14. Risk manual acknowledgement
def test_risk_manual_acknowledgement():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "ack-test", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now - timedelta(days=25)))
        db.commit()

        risk_service.evaluate_and_persist_risks(proj.id, db)
        risk = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == proj.id).first()

        ack_risk = risk_service.acknowledge_risk(risk.id, proj.id, db)
        assert ack_risk.status == "ACKNOWLEDGED"
        assert ack_risk.acknowledged_at is not None
    finally:
        db.close()


# 15. Health snapshot persistence
def test_health_snapshot_persistence():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "persist", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now))
        db.commit()

        snapshot = health_service.calculate_and_persist_health(proj.id, db)
        assert snapshot.id is not None

        queried = db.query(SoftwareHealthSnapshot).filter(SoftwareHealthSnapshot.id == snapshot.id).first()
        assert queried is not None
        assert queried.overall_score == snapshot.overall_score
        assert len(queried.dimensions) == 6
    finally:
        db.close()


# 16. Health history retrieval
def test_health_history_retrieval():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "history", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Init", author_name="Dev", author_date=now))
        db.commit()

        # Compute twice
        s1 = health_service.calculate_and_persist_health(proj.id, db, twin_version=1)
        s2 = health_service.calculate_and_persist_health(proj.id, db, twin_version=2)

        history = health_service.get_health_history(proj.id, db)
        assert len(history) >= 2
        assert history[0].id == s1.id
        assert history[1].id == s2.id
    finally:
        db.close()


# 17. Repository isolation between Project A and Project B
def test_repository_isolation():
    db = SessionLocal()
    try:
        proj_a = create_test_project(db, "org-a", "repo-a")
        proj_b = create_test_project(db, "org-b", "repo-b")
        now = datetime.now(timezone.utc)

        # Proj A has inactive risk
        db.add(Commit(project_id=proj_a.id, sha="a001", message="A commit", author_name="Dev A", author_date=now - timedelta(days=25)))
        # Proj B has active commit
        db.add(Commit(project_id=proj_b.id, sha="b001", message="B commit", author_name="Dev B", author_date=now))
        db.commit()

        health_service.calculate_and_persist_health(proj_a.id, db)
        health_service.calculate_and_persist_health(proj_b.id, db)

        risk_service.evaluate_and_persist_risks(proj_a.id, db)
        risk_service.evaluate_and_persist_risks(proj_b.id, db)

        risks_a = risk_service.get_risks(proj_a.id, db)
        risks_b = risk_service.get_risks(proj_b.id, db)

        # Proj A has inactivity risk, Proj B has none
        assert len(risks_a) == 1
        assert len(risks_b) == 0

        # API isolation check
        res_a = client.get(f"/api/v1/projects/{proj_a.id}/risks")
        res_b = client.get(f"/api/v1/projects/{proj_b.id}/risks")
        assert res_a.status_code == 200
        assert res_b.status_code == 200
        assert len(res_a.json()) == 1
        assert len(res_b.json()) == 0
    finally:
        db.close()


# 18. Project switching behavior
def test_project_switching_behavior():
    db = SessionLocal()
    try:
        proj_a = create_test_project(db, "switch-a", "repo-a")
        proj_b = create_test_project(db, "switch-b", "repo-b")
        now = datetime.now(timezone.utc)

        db.add(Commit(project_id=proj_a.id, sha="a001", message="A", author_name="Dev A", author_date=now - timedelta(days=20)))
        db.add(Commit(project_id=proj_b.id, sha="b001", message="B", author_name="Dev B", author_date=now - timedelta(days=1)))
        db.commit()

        client.get(f"/api/v1/projects/{proj_a.id}/health")
        client.get(f"/api/v1/projects/{proj_b.id}/health")

        # Query A
        res_a = client.get(f"/api/v1/projects/{proj_a.id}/health")
        # Query B
        res_b = client.get(f"/api/v1/projects/{proj_b.id}/health")

        data_a = res_a.json()
        data_b = res_b.json()

        assert data_a["project_id"] == proj_a.id
        assert data_b["project_id"] == proj_b.id
        assert data_a["project_id"] != data_b["project_id"]
    finally:
        db.close()


# 19. Digital Twin stale state visibility
def test_digital_twin_stale_state():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "stale-twin", "repo")
        now = datetime.now(timezone.utc)
        twin = DigitalTwin(
            project_id=proj.id,
            current_version=1,
            status="ACTIVE",
            last_synced_at=now - timedelta(minutes=120),  # threshold is 60m
            stale_threshold_minutes=60,
        )
        db.add(twin)
        db.commit()

        twin_data = digital_twin_service.get_twin_response_data(twin)
        assert twin_data["is_outdated"] is True
    finally:
        db.close()


# 20. GitHub API failure handling
def test_github_api_failure_handling():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "fail-test", "repo")
        twin = digital_twin_service.get_or_create_twin(proj.id, db)

        async def run_fail():
            with patch("app.services.digital_twin_service.github_service.get_repo_details", new_callable=AsyncMock) as m_meta:
                m_meta.side_effect = Exception("GitHub API Down")
                with pytest.raises(Exception):
                    await digital_twin_service.synchronize_twin(proj.id, db)

        asyncio.run(run_fail())
        db.refresh(twin)
        assert twin.status == "ERROR"
    finally:
        db.close()


# 21. No duplicate risks after repeated synchronization
def test_no_duplicate_risks_repeated_synchronization():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "sync-dedup", "repo")
        now = datetime.now(timezone.utc)
        db.add(Commit(project_id=proj.id, sha="c001", message="Old", author_name="Dev", author_date=now - timedelta(days=20)))
        db.add(Issue(project_id=proj.id, number=1, title="Stale Issue", state="open", created_at=now - timedelta(days=40)))
        db.commit()

        # Simulate 3 sync runs
        risk_service.evaluate_and_persist_risks(proj.id, db)
        risk_service.evaluate_and_persist_risks(proj.id, db)
        risk_service.evaluate_and_persist_risks(proj.id, db)

        count = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == proj.id).count()
        assert count == 2  # exactly 1 inactivity risk + 1 stale issue risk, no triples
    finally:
        db.close()


# 22. No fake data when metrics are unavailable
def test_no_fake_data_when_metrics_unavailable():
    db = SessionLocal()
    try:
        proj = create_test_project(db, "empty-repo", "repo")
        # 0 commits, 0 issues, 0 PRs, 0 releases
        snapshot = health_service.calculate_and_persist_health(proj.id, db)
        assert snapshot.overall_score == 0.0
        assert snapshot.overall_status == "INSUFFICIENT_DATA"

        for dim in snapshot.dimensions:
            assert dim.status == "INSUFFICIENT_DATA"
            assert dim.score is None
    finally:
        db.close()
