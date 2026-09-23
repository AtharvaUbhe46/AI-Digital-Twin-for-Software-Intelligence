import re
import logging
from typing import Tuple, Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("digital_twin.github")


class GitHubAPIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class GitHubRepoNotFoundError(GitHubAPIError):
    def __init__(self, owner: str, repo: str):
        super().__init__(f"Repository '{owner}/{repo}' not found on GitHub.", status_code=404)


class GitHubRateLimitError(GitHubAPIError):
    def __init__(self, reset_time: Optional[str] = None):
        super().__init__(
            f"GitHub API rate limit exceeded. Reset time: {reset_time or 'soon'}. Add GITHUB_TOKEN in .env for 5,000 req/hr.",
            status_code=429
        )


class GitHubInvalidURLError(GitHubAPIError):
    def __init__(self, url: str):
        super().__init__(f"Invalid GitHub repository URL: '{url}'. Use format 'https://github.com/owner/repo' or 'owner/repo'.", status_code=400)


def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parses a GitHub repository URL or slug into (owner, repo).
    Supports:
        https://github.com/facebook/react
        https://github.com/facebook/react.git
        github.com/facebook/react/
        facebook/react
    """
    if not url or not isinstance(url, str):
        raise GitHubInvalidURLError(str(url))

    cleaned = url.strip()

    # Remove protocol
    cleaned = re.sub(r"^https?://", "", cleaned)
    # Remove github.com/
    cleaned = re.sub(r"^www\.", "", cleaned)
    cleaned = re.sub(r"^github\.com/", "", cleaned)
    # Remove trailing .git and trailing slashes
    cleaned = re.sub(r"\.git$", "", cleaned)
    cleaned = cleaned.strip("/")

    parts = cleaned.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise GitHubInvalidURLError(url)

    owner = parts[0].strip()
    repo = parts[1].strip()

    valid_pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")
    if not valid_pattern.match(owner) or not valid_pattern.match(repo):
        raise GitHubInvalidURLError(url)

    return owner, repo


class GitHubService:
    def __init__(self):
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AIDigitalTwin-SoftwareIntelligence/1.0",
        }
        if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip():
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"
        return headers

    async def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
            except httpx.RequestError as exc:
                logger.error(f"Network error contacting GitHub API {url}: {exc}")
                raise GitHubAPIError(f"Failed to communicate with GitHub API: {str(exc)}", status_code=502)

        # Check rate limits
        remaining = response.headers.get("x-ratelimit-remaining")
        reset_time = response.headers.get("x-ratelimit-reset")
        if response.status_code in (403, 429) and remaining == "0":
            raise GitHubRateLimitError(reset_time)

        if response.status_code == 404:
            raise GitHubAPIError("Resource not found on GitHub", status_code=404)

        if response.status_code >= 400:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            msg = error_data.get("message", f"GitHub API error: HTTP {response.status_code}")
            raise GitHubAPIError(msg, status_code=response.status_code)

        return response.json()

    async def get_repo_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch metadata for owner/repo"""
        try:
            return await self._request(f"/repos/{owner}/{repo}")
        except GitHubAPIError as e:
            if e.status_code == 404:
                raise GitHubRepoNotFoundError(owner, repo)
            raise

    async def get_contributors(self, owner: str, repo: str, per_page: int = 30) -> List[Dict[str, Any]]:
        """Fetch contributors list"""
        try:
            res = await self._request(f"/repos/{owner}/{repo}/contributors", params={"per_page": per_page})
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch contributors for {owner}/{repo}: {e}")
            return []

    async def get_commits(self, owner: str, repo: str, per_page: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent commits"""
        try:
            res = await self._request(f"/repos/{owner}/{repo}/commits", params={"per_page": per_page})
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch commits for {owner}/{repo}: {e}")
            return []

    async def get_issues(self, owner: str, repo: str, state: str = "all", per_page: int = 50) -> List[Dict[str, Any]]:
        """Fetch issues (excluding pull requests)"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/issues",
                params={"state": state, "per_page": per_page, "sort": "created", "direction": "desc"}
            )
            if not isinstance(res, list):
                return []
            # In GitHub API, issues list contains pull requests unless filtered out!
            return [item for item in res if item.get("pull_request") is None]
        except Exception as e:
            logger.warning(f"Could not fetch issues for {owner}/{repo}: {e}")
            return []

    async def get_pull_requests(self, owner: str, repo: str, state: str = "all", per_page: int = 50) -> List[Dict[str, Any]]:
        """Fetch pull requests"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/pulls",
                params={"state": state, "per_page": per_page, "sort": "created", "direction": "desc"}
            )
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch pull requests for {owner}/{repo}: {e}")
            return []

    async def get_releases(self, owner: str, repo: str, per_page: int = 20) -> List[Dict[str, Any]]:
        """Fetch releases"""
        try:
            res = await self._request(f"/repos/{owner}/{repo}/releases", params={"per_page": per_page})
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch releases for {owner}/{repo}: {e}")
            return []

    async def get_branches(self, owner: str, repo: str, per_page: int = 30) -> List[Dict[str, Any]]:
        """Fetch branches"""
        try:
            res = await self._request(f"/repos/{owner}/{repo}/branches", params={"per_page": per_page})
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch branches for {owner}/{repo}: {e}")
            return []

    async def get_repo_tree(self, owner: str, repo: str, tree_sha: str = "main") -> List[Dict[str, Any]]:
        """Fetch repository file tree recursively (up to 1000 items)"""
        try:
            res = await self._request(f"/repos/{owner}/{repo}/git/trees/{tree_sha}", params={"recursive": "1"})
            if isinstance(res, dict) and "tree" in res and isinstance(res["tree"], list):
                return res["tree"]
            return []
        except Exception as e:
            logger.warning(f"Could not fetch git tree for {owner}/{repo} at {tree_sha}: {e}")
            return []

    async def get_rate_limit(self) -> Dict[str, Any]:
        """Fetch current rate limit status"""
        try:
            return await self._request("/rate_limit")
        except Exception as e:
            logger.warning(f"Could not check rate limit: {e}")
            return {
                "resources": {
                    "core": {
                        "limit": 60,
                        "remaining": 60,
                        "reset": 0
                    }
                }
            }


github_service = GitHubService()
