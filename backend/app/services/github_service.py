import re
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("digital_twin.github")


class GitHubAPIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class GitHubAuthError(GitHubAPIError):
    def __init__(self, message: str = "Invalid or expired GitHub Personal Access Token."):
        super().__init__(message, status_code=401)


class GitHubRepoNotFoundError(GitHubAPIError):
    def __init__(self, owner: str, repo: str):
        super().__init__(f"Repository '{owner}/{repo}' not found on GitHub.", status_code=404)


class GitHubRateLimitError(GitHubAPIError):
    def __init__(self, reset_time: Optional[str] = None, message: Optional[str] = None):
        msg = message or f"GitHub API rate limit exceeded. Reset time: {reset_time or 'soon'}."
        super().__init__(msg, status_code=429)


class GitHubInvalidURLError(GitHubAPIError):
    def __init__(self, url: str):
        super().__init__(
            f"Invalid GitHub repository URL: '{url}'. Use format 'https://github.com/owner/repo' or 'owner/repo'.",
            status_code=400,
        )


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
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, Dict[str, Any]] = {}

        # In-memory rate limit state tracked dynamically from real GitHub responses
        self.rate_limit_state: Dict[str, Any] = {
            "limit": 5000 if bool(settings.GITHUB_TOKEN) else 60,
            "remaining": 5000 if bool(settings.GITHUB_TOKEN) else 60,
            "used": 0,
            "reset": 0,
            "resource": "core",
            "authenticated": bool(settings.GITHUB_TOKEN),
            "connected": True,
            "status": "connected" if bool(settings.GITHUB_TOKEN) else "token_not_configured",
            "last_synced_at": None,
            "search_limit": None,
            "search_remaining": None,
            "graphql_limit": None,
            "graphql_remaining": None,
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Reuse HTTP client and connection pool for high performance and reliability."""
        loop = asyncio.get_running_loop()
        if self._client is None or self._client.is_closed or getattr(self, "_loop", None) != loop:
            if self._client and not self._client.is_closed:
                try:
                    await self._client.aclose()
                except Exception:
                    pass
            self._loop = loop
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=8.0),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=40),
            )
        return self._client

    async def close(self):
        """Cleanly close persistent HTTP client on shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> Dict[str, str]:
        """
        Builds standard authenticated or unauthenticated GitHub API headers.
        Never logs or exposes the token.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AIDigitalTwin-SoftwareIntelligence/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = settings.GITHUB_TOKEN
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def _update_rate_limits_from_headers(self, headers: httpx.Headers):
        """Dynamically intercepts rate-limit headers from ANY standard GitHub API response."""
        limit = headers.get("x-ratelimit-limit")
        remaining = headers.get("x-ratelimit-remaining")
        used = headers.get("x-ratelimit-used")
        reset_ts = headers.get("x-ratelimit-reset")
        resource = headers.get("x-ratelimit-resource", "core")

        if limit is not None:
            try:
                l_val = int(limit)
                self.rate_limit_state["limit"] = l_val
                # Authenticated PAT quotas are 5,000+ requests/hour
                if l_val >= 1000:
                    self.rate_limit_state["authenticated"] = True
                    self.rate_limit_state["status"] = "connected"
                elif not settings.GITHUB_TOKEN:
                    self.rate_limit_state["authenticated"] = False
                    self.rate_limit_state["status"] = "token_not_configured"
            except (ValueError, TypeError):
                pass

        if remaining is not None:
            try:
                self.rate_limit_state["remaining"] = int(remaining)
            except (ValueError, TypeError):
                pass

        if used is not None:
            try:
                self.rate_limit_state["used"] = int(used)
            except (ValueError, TypeError):
                pass

        if reset_ts is not None:
            try:
                self.rate_limit_state["reset"] = int(reset_ts)
            except (ValueError, TypeError):
                pass

        if resource:
            self.rate_limit_state["resource"] = resource

        self.rate_limit_state["connected"] = True

    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        max_retries: int = 2,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Cache key for ETag / 304 conditional request
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        cached_item = self._cache.get(cache_key) if use_cache else None

        if cached_item and "etag" in cached_item:
            headers["If-None-Match"] = cached_item["etag"]

        client = await self._get_client()

        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                response = await client.get(url, headers=headers, params=params)
                break
            except (httpx.RequestError, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                logger.error(f"Network error contacting GitHub API {url}: {exc}")
                self.rate_limit_state["connected"] = False
                self.rate_limit_state["status"] = "unreachable"
                raise GitHubAPIError(f"Failed to communicate with GitHub API: {str(exc)}", status_code=502)

        # Intercept and record actual rate limits from response headers
        self._update_rate_limits_from_headers(response.headers)

        # 304 Not Modified: return cached payload directly (preserves quota)
        if response.status_code == 304 and cached_item:
            logger.debug(f"GitHub API 304 Not Modified for {endpoint} (using cached data)")
            return cached_item["data"]

        # 401 Unauthorized: Invalid or expired PAT
        if response.status_code == 401:
            self.rate_limit_state["authenticated"] = False
            self.rate_limit_state["status"] = "auth_failed"
            logger.error("GitHub API 401 Unauthorized: Check GITHUB_TOKEN in root .env")
            raise GitHubAuthError(
                "GitHub Personal Access Token is invalid, expired, or revoked. Please verify GITHUB_TOKEN in your .env file."
            )

        # 403 / 429: Rate limit exceeded or secondary rate limit
        if response.status_code in (403, 429):
            remaining = response.headers.get("x-ratelimit-remaining")
            reset_time = response.headers.get("x-ratelimit-reset")
            self.rate_limit_state["status"] = "rate_limited"
            if remaining == "0":
                raise GitHubRateLimitError(reset_time)
            # Secondary rate limit or abuse detection
            err_msg = "GitHub secondary rate limit triggered or access forbidden. Please wait before retrying."
            try:
                err_body = response.json()
                if "message" in err_body:
                    err_msg = f"GitHub API: {err_body['message']}"
            except Exception:
                pass
            raise GitHubRateLimitError(reset_time, message=err_msg)

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

        data = response.json()

        # Cache with ETag for conditional requests if available
        etag = response.headers.get("ETag")
        if etag and use_cache:
            self._cache[cache_key] = {
                "etag": etag,
                "data": data,
                "cached_at": time.time(),
            }

        return data

    async def get_repo_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch metadata for owner/repo"""
        try:
            return await self._request(f"/repos/{owner}/{repo}")
        except GitHubAPIError as e:
            if e.status_code == 404:
                raise GitHubRepoNotFoundError(owner, repo)
            raise

    async def get_contributors(self, owner: str, repo: str, per_page: int = 30, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch contributors list with pagination support"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/contributors",
                params={"per_page": per_page, "page": page},
            )
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch contributors for {owner}/{repo}: {e}")
            return []

    async def get_commits(self, owner: str, repo: str, per_page: int = 50, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch recent commits with pagination support"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/commits",
                params={"per_page": per_page, "page": page},
            )
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch commits for {owner}/{repo}: {e}")
            return []

    async def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        per_page: int = 50,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """Fetch issues (excluding pull requests) with pagination support"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/issues",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            if not isinstance(res, list):
                return []
            # In GitHub API, issues list contains pull requests unless filtered out!
            return [item for item in res if item.get("pull_request") is None]
        except Exception as e:
            logger.warning(f"Could not fetch issues for {owner}/{repo}: {e}")
            return []

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        per_page: int = 50,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """Fetch pull requests with pagination support"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/pulls",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch pull requests for {owner}/{repo}: {e}")
            return []

    async def get_releases(self, owner: str, repo: str, per_page: int = 20, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch releases with pagination support"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/releases",
                params={"per_page": per_page, "page": page},
            )
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch releases for {owner}/{repo}: {e}")
            return []

    async def get_branches(self, owner: str, repo: str, per_page: int = 30, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch branches with pagination support"""
        try:
            res = await self._request(
                f"/repos/{owner}/{repo}/branches",
                params={"per_page": per_page, "page": page},
            )
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch branches for {owner}/{repo}: {e}")
            return []

    async def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Fetch repository programming languages breakdown"""
        try:
            res = await self._request(f"/repos/{owner}/{repo}/languages")
            return res if isinstance(res, dict) else {}
        except Exception as e:
            logger.warning(f"Could not fetch languages for {owner}/{repo}: {e}")
            return {}

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

    async def get_commit_details(self, owner: str, repo: str, sha: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed commit info including file-level additions/deletions.
        Used for hotspot analysis during sync.
        """
        try:
            return await self._request(f"/repos/{owner}/{repo}/commits/{sha}")
        except Exception as e:
            logger.debug(f"Could not fetch commit details for {sha[:7]} in {owner}/{repo}: {e}")
            return None

    async def get_file_content(self, owner: str, repo: str, path: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single file's content from the default branch via GitHub Contents API.
        Returns the raw API response dict (with base64-encoded 'content' field) or None.
        """
        try:
            return await self._request(f"/repos/{owner}/{repo}/contents/{path}")
        except Exception as e:
            logger.debug(f"File '{path}' not found in {owner}/{repo}: {e}")
            return None

    async def get_rate_limit(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Queries the authenticated GET https://api.github.com/rate_limit endpoint.
        Captures core, search, and graphql quotas and updates internal state.
        """
        try:
            data = await self._request("/rate_limit", use_cache=not force_refresh)
            resources = data.get("resources", {})
            core = resources.get("core", {})
            search = resources.get("search", {})
            graphql = resources.get("graphql", {})

            if core:
                self.rate_limit_state["limit"] = core.get("limit", self.rate_limit_state["limit"])
                self.rate_limit_state["remaining"] = core.get("remaining", self.rate_limit_state["remaining"])
                self.rate_limit_state["used"] = core.get("used", self.rate_limit_state["used"])
                self.rate_limit_state["reset"] = core.get("reset", self.rate_limit_state["reset"])

            if search:
                self.rate_limit_state["search_limit"] = search.get("limit")
                self.rate_limit_state["search_remaining"] = search.get("remaining")

            if graphql:
                self.rate_limit_state["graphql_limit"] = graphql.get("limit")
                self.rate_limit_state["graphql_remaining"] = graphql.get("remaining")

            if self.rate_limit_state["limit"] >= 1000:
                self.rate_limit_state["authenticated"] = True
                self.rate_limit_state["status"] = "connected"
            elif not settings.GITHUB_TOKEN:
                self.rate_limit_state["authenticated"] = False
                self.rate_limit_state["status"] = "token_not_configured"

            return data
        except GitHubAuthError:
            self.rate_limit_state["authenticated"] = False
            self.rate_limit_state["status"] = "auth_failed"
            raise
        except Exception as e:
            logger.warning(f"Could not refresh rate limit from GitHub API: {e}")
            return {
                "resources": {
                    "core": {
                        "limit": self.rate_limit_state["limit"],
                        "remaining": self.rate_limit_state["remaining"],
                        "used": self.rate_limit_state["used"],
                        "reset": self.rate_limit_state["reset"],
                    }
                }
            }

    def record_sync_time(self):
        """Records last successful synchronization timestamp."""
        self.rate_limit_state["last_synced_at"] = datetime.now(timezone.utc)


github_service = GitHubService()
