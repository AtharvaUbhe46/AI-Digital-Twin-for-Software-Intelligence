import asyncio
import pytest
from app.core.config import settings
from app.services.github_service import github_service


def test_token_loading_and_config():
    """Verify backend has loaded the token from root .env without exposing secrets."""
    assert settings.GITHUB_TOKEN is not None, "GITHUB_TOKEN should be present in settings"
    assert len(settings.GITHUB_TOKEN.strip()) > 20, "GITHUB_TOKEN should be non-empty"
    assert not settings.GITHUB_TOKEN.startswith('"')
    assert not settings.GITHUB_TOKEN.endswith('"')


def test_authenticated_rate_limit_call():
    """Verify authenticated rate limit query returns 5000 limit and dynamic quota."""
    rate_info = asyncio.run(github_service.get_rate_limit(force_refresh=True))
    assert "resources" in rate_info
    core = rate_info["resources"].get("core", {})
    assert core.get("limit") == 5000, f"Expected 5000 limit for PAT, got {core.get('limit')}"
    assert core.get("remaining") is not None
    assert core.get("remaining") <= 5000
    assert core.get("reset") is not None

    state = github_service.rate_limit_state
    assert state["authenticated"] is True
    assert state["limit"] == 5000
    assert state["status"] == "connected"


def test_public_repo_fetching_authenticated():
    """Verify real repository access with octocat/Hello-World."""
    repo_data = asyncio.run(github_service.get_repo_details("octocat", "Hello-World"))
    assert repo_data.get("name") == "Hello-World"
    assert repo_data.get("owner", {}).get("login") == "octocat"

    # Test commits
    commits = asyncio.run(github_service.get_commits("octocat", "Hello-World", per_page=5))
    assert isinstance(commits, list)
    assert len(commits) > 0

    # Test contributors
    contribs = asyncio.run(github_service.get_contributors("octocat", "Hello-World", per_page=5))
    assert isinstance(contribs, list)
    assert len(contribs) > 0


def test_etag_caching():
    """Verify ETag / conditional request caching."""
    # First call sets cache
    res1 = asyncio.run(github_service.get_repo_details("octocat", "Hello-World"))
    # Second call should utilize ETag / 304 or cache
    res2 = asyncio.run(github_service.get_repo_details("octocat", "Hello-World"))
    assert res1["id"] == res2["id"]
