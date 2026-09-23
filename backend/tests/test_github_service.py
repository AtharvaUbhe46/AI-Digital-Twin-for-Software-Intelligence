import pytest
from app.services.github_service import parse_github_url, GitHubInvalidURLError
from app.services.sync_service import calculate_repository_health_index


def test_parse_github_url_valid():
    cases = [
        ("https://github.com/facebook/react", ("facebook", "react")),
        ("https://github.com/facebook/react.git", ("facebook", "react")),
        ("http://github.com/facebook/react/", ("facebook", "react")),
        ("github.com/facebook/react", ("facebook", "react")),
        ("facebook/react", ("facebook", "react")),
        ("https://github.com/microsoft/vscode", ("microsoft", "vscode")),
        ("octocat/Hello-World", ("octocat", "Hello-World")),
    ]
    for input_url, expected in cases:
        owner, repo = parse_github_url(input_url)
        assert (owner, repo) == expected, f"Failed on input: {input_url}"


def test_parse_github_url_invalid():
    invalid_cases = [
        "",
        "   ",
        "https://google.com",
        "justastring",
        "facebook/",
        "/react",
        "http://github.com/",
        "https://github.com/invalid spaces/repo",
    ]
    for bad_url in invalid_cases:
        with pytest.raises(GitHubInvalidURLError):
            parse_github_url(bad_url)


def test_calculate_repository_health_index_deterministic():
    # Test with simulated mock items
    sample_commits = [
        {"commit": {"author": {"date": "2026-09-20T12:00:00Z", "name": "Dev 1"}}},
        {"commit": {"author": {"date": "2026-09-18T12:00:00Z", "name": "Dev 2"}}},
    ]
    sample_issues = [
        {"state": "closed"},
        {"state": "closed"},
        {"state": "open"},
    ]
    sample_prs = [
        {"state": "closed", "merged_at": "2026-09-19T10:00:00Z"},
        {"state": "open", "merged_at": None},
    ]
    sample_contribs = [{"login": "user1"}, {"login": "user2"}, {"login": "user3"}]

    health = calculate_repository_health_index(
        commits=sample_commits,
        issues=sample_issues,
        pull_requests=sample_prs,
        contributors=sample_contribs,
        stars_count=150,
        open_issues_count=1,
    )

    assert "score" in health
    assert 0 <= health["score"] <= 100
    assert "formula" in health
    assert len(health["components"]) == 4
    for comp in health["components"]:
        assert "score" in comp
        assert "max_score" in comp
        assert "weight" in comp
