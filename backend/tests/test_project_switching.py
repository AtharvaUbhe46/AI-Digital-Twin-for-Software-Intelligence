import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_REPO_A = {
    "name": "react",
    "description": "The library for web and native user interfaces.",
    "html_url": "https://github.com/facebook/react",
    "default_branch": "main",
    "language": "JavaScript",
    "visibility": "public",
    "stargazers_count": 225000,
    "forks_count": 45000,
    "subscribers_count": 6600,
    "open_issues_count": 850,
    "created_at": "2013-05-24T16:15:54Z",
    "updated_at": "2026-09-20T10:00:00Z",
    "pushed_at": "2026-09-21T09:00:00Z",
}

MOCK_REPO_B = {
    "name": "vscode",
    "description": "Visual Studio Code",
    "html_url": "https://github.com/microsoft/vscode",
    "default_branch": "main",
    "language": "TypeScript",
    "visibility": "public",
    "stargazers_count": 160000,
    "forks_count": 28000,
    "subscribers_count": 3200,
    "open_issues_count": 4500,
    "created_at": "2015-09-03T20:23:38Z",
    "updated_at": "2026-09-21T11:00:00Z",
    "pushed_at": "2026-09-22T08:00:00Z",
}

MOCK_COMMITS_A = [
    {
        "sha": "a111111111111111111111111111111111111111",
        "commit": {"message": "React commit A1", "author": {"name": "React Dev", "date": "2026-09-21T10:00:00Z"}},
        "author": {"login": "react-core", "avatar_url": "https://avatars.githubusercontent.com/u/1"},
        "html_url": "https://github.com/facebook/react/commit/a1",
    }
]

MOCK_COMMITS_B = [
    {
        "sha": "b222222222222222222222222222222222222222",
        "commit": {"message": "VS Code commit B1", "author": {"name": "VSCode Dev", "date": "2026-09-21T11:00:00Z"}},
        "author": {"login": "vscode-team", "avatar_url": "https://avatars.githubusercontent.com/u/2"},
        "html_url": "https://github.com/microsoft/vscode/commit/b1",
    },
    {
        "sha": "b33333333333333333333333333333333333333",
        "commit": {"message": "VS Code commit B2", "author": {"name": "VSCode Dev 2", "date": "2026-09-20T11:00:00Z"}},
        "author": {"login": "vscode-team-2", "avatar_url": "https://avatars.githubusercontent.com/u/3"},
        "html_url": "https://github.com/microsoft/vscode/commit/b2",
    }
]


def test_repository_connection_and_switching_isolation():
    """
    Mandatory Integration Test:
    1. Connect Repository A (facebook/react) -> verify its metrics
    2. Connect Repository B (microsoft/vscode) -> verify Repository B metrics
    3. Switch to B -> verify B is active and data matches B
    4. Switch back to A -> verify A is active and data returns to A
    5. Verify zero leakage between A and B
    """
    with patch("app.services.github_service.github_service.get_repo_details", new_callable=AsyncMock) as mock_details, \
         patch("app.services.github_service.github_service.get_contributors", new_callable=AsyncMock) as mock_contribs, \
         patch("app.services.github_service.github_service.get_commits", new_callable=AsyncMock) as mock_commits, \
         patch("app.services.github_service.github_service.get_issues", new_callable=AsyncMock) as mock_issues, \
         patch("app.services.github_service.github_service.get_pull_requests", new_callable=AsyncMock) as mock_prs, \
         patch("app.services.github_service.github_service.get_releases", new_callable=AsyncMock) as mock_releases, \
         patch("app.services.github_service.github_service.get_branches", new_callable=AsyncMock) as mock_branches:

        # Step 1: Connect Repository A (facebook/react)
        mock_details.return_value = MOCK_REPO_A
        mock_contribs.return_value = [{"login": "gaearon", "contributions": 1200, "avatar_url": "https://avatars.com/1"}]
        mock_commits.return_value = MOCK_COMMITS_A
        mock_issues.return_value = [{"number": 101, "title": "React issue 1", "state": "open", "labels": []}]
        mock_prs.return_value = [{"number": 201, "title": "React PR 1", "state": "open", "merged_at": None}]
        mock_releases.return_value = [{"tag_name": "v19.0.0", "name": "React 19"}]
        mock_branches.return_value = [{"name": "main", "commit": {"sha": "a111"}}]

        resp_a = client.post("/api/v1/projects/connect", json={"repo_url": "https://github.com/facebook/react"})
        assert resp_a.status_code == 201
        data_a = resp_a.json()
        project_a_id = data_a["id"]
        assert data_a["full_name"] == "facebook/react"
        assert data_a["stars_count"] == 225000

        # Verify Dashboard for A
        dash_a = client.get(f"/api/v1/projects/{project_a_id}/dashboard").json()
        assert dash_a["full_name"] == "facebook/react"
        assert dash_a["total_commits"] == 1
        assert dash_a["total_contributors"] == 1
        assert dash_a["open_issues"] == 850

        # Verify Overview for A
        overview_a = client.get(f"/api/v1/projects/{project_a_id}/overview").json()
        assert overview_a["identity"]["full_name"] == "facebook/react"
        assert overview_a["identity"]["language"] == "JavaScript"
        assert overview_a["statistics"]["stars"] == 225000

        # Step 2: Connect Repository B (microsoft/vscode)
        mock_details.return_value = MOCK_REPO_B
        mock_contribs.return_value = [
            {"login": "bpasero", "contributions": 2500, "avatar_url": "https://avatars.com/2"},
            {"login": "jrieken", "contributions": 2200, "avatar_url": "https://avatars.com/3"}
        ]
        mock_commits.return_value = MOCK_COMMITS_B
        mock_issues.return_value = [{"number": 501, "title": "VS Code issue 1", "state": "open", "labels": []}]
        mock_prs.return_value = [{"number": 601, "title": "VS Code PR 1", "state": "open", "merged_at": None}]
        mock_releases.return_value = [{"tag_name": "1.92.0", "name": "July 2026"}]
        mock_branches.return_value = [{"name": "main", "commit": {"sha": "b222"}}]

        resp_b = client.post("/api/v1/projects/connect", json={"repo_url": "microsoft/vscode"})
        assert resp_b.status_code == 201
        data_b = resp_b.json()
        project_b_id = data_b["id"]
        assert data_b["full_name"] == "microsoft/vscode"
        assert data_b["stars_count"] == 160000

        # Verify B is now the active project
        active_resp = client.get("/api/v1/projects/active").json()
        assert active_resp["id"] == project_b_id
        assert active_resp["full_name"] == "microsoft/vscode"

        # Verify Dashboard for B has B's metrics (2 commits, 2 contributors, 4500 issues)
        dash_b = client.get(f"/api/v1/projects/{project_b_id}/dashboard").json()
        assert dash_b["full_name"] == "microsoft/vscode"
        assert dash_b["total_commits"] == 2
        assert dash_b["total_contributors"] == 2
        assert dash_b["open_issues"] == 4500

        # Verify Overview for B
        overview_b = client.get(f"/api/v1/projects/{project_b_id}/overview").json()
        assert overview_b["identity"]["full_name"] == "microsoft/vscode"
        assert overview_b["identity"]["language"] == "TypeScript"
        assert overview_b["statistics"]["stars"] == 160000

        # Step 3: Switch back to Repository A
        switch_resp = client.post(f"/api/v1/projects/{project_a_id}/activate")
        assert switch_resp.status_code == 200
        assert switch_resp.json()["full_name"] == "facebook/react"

        # Verify active project is now A
        active_now = client.get("/api/v1/projects/active").json()
        assert active_now["id"] == project_a_id
        assert active_now["full_name"] == "facebook/react"

        # Verify active dashboard returns A's data without any leakage from B
        dash_active = client.get("/api/v1/projects/active/dashboard").json()
        assert dash_active["full_name"] == "facebook/react"
        assert dash_active["total_commits"] == 1
        assert dash_active["total_contributors"] == 1
        assert dash_active["open_issues"] == 850
        assert dash_active["total_commits"] != dash_b["total_commits"]

        # Verify active overview returns A's data
        overview_active = client.get("/api/v1/projects/active/overview").json()
        assert overview_active["identity"]["full_name"] == "facebook/react"
        assert overview_active["identity"]["language"] == "JavaScript"
        assert overview_active["statistics"]["stars"] == 225000
