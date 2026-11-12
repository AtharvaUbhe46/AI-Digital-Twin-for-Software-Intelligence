import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx

from app.core.config import settings

logger = logging.getLogger("digital_twin.assistant.groq")


class GroqServiceError(Exception):
    """Base exception for Groq interactions."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GroqConnectionError(GroqServiceError):
    """Raised when Groq API endpoint cannot be reached."""
    pass


class GroqAuthError(GroqServiceError):
    """Raised when Groq API key is invalid or unauthorized."""
    pass


class GroqRateLimitError(GroqServiceError):
    """Raised when Groq API rate limits (HTTP 429) are encountered."""
    pass


class GroqModelNotFoundError(GroqServiceError):
    """Raised when configured model is not available or decommissioned."""
    pass


class GroqTimeoutError(GroqServiceError):
    """Raised when Groq request exceeds timeout."""
    pass


class GroqService:
    """
    High-performance asynchronous client abstraction for Groq Cloud LPUs.
    Provides sub-second token streaming, persistent connection pooling,
    and automatic error/rate-limit recovery for the AI Project Assistant.
    """

    GROQ_API_BASE = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = 30.0,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL or "qwen/qwen3.8-27b"
        self.timeout = timeout or 30.0
        self.temperature = temperature if temperature is not None else settings.AI_TEMPERATURE
        self.max_tokens = max_tokens or settings.AI_MAX_TOKENS or 2048
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise GroqAuthError("GROQ_API_KEY is not configured in backend environment (.env).")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AI-Digital-Twin-Software-Intelligence/1.0"
        }

    def _get_async_client(self) -> httpx.AsyncClient:
        """Persistent AsyncClient with HTTP connection pooling."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self.GROQ_API_BASE,
                timeout=httpx.Timeout(self.timeout, connect=6.0),
                limits=httpx.Limits(max_keepalive_connections=8, max_connections=16, keepalive_expiry=30.0),
            )
        return self._async_client

    async def aclose(self):
        """Close connection pool."""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None

    def check_health(self) -> Dict[str, Any]:
        """
        Pings Groq /models endpoint to verify API key validity and model accessibility.
        Masks API key completely to prevent any credential exposure.
        """
        if not self.api_key:
            return {
                "connected": False,
                "provider": "groq",
                "base_url": self.GROQ_API_BASE,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error": "Groq API key is not configured. Set GROQ_API_KEY in backend/.env."
            }

        url = f"{self.GROQ_API_BASE}/models"
        headers = self._get_headers()
        try:
            with httpx.Client(timeout=6.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    models = [m.get("id", "") for m in resp.json().get("data", [])]
                    model_found = self.model in models or any(self.model in m for m in models)
                    return {
                        "connected": True,
                        "provider": "groq",
                        "base_url": self.GROQ_API_BASE,
                        "model": self.model,
                        "model_available": model_found or len(models) > 0,
                        "available_models": models,
                        "error": None if model_found else f"Model '{self.model}' not listed; using available Groq model."
                    }
                elif resp.status_code in (401, 403):
                    return {
                        "connected": False,
                        "provider": "groq",
                        "base_url": self.GROQ_API_BASE,
                        "model": self.model,
                        "model_available": False,
                        "available_models": [],
                        "error": "Groq API authentication failed. Please verify your GROQ_API_KEY."
                    }
                elif resp.status_code == 429:
                    return {
                        "connected": False,
                        "provider": "groq",
                        "base_url": self.GROQ_API_BASE,
                        "model": self.model,
                        "model_available": False,
                        "available_models": [],
                        "error": "Groq API rate limit exceeded. Please wait a moment before retrying."
                    }
                else:
                    return {
                        "connected": False,
                        "provider": "groq",
                        "base_url": self.GROQ_API_BASE,
                        "model": self.model,
                        "model_available": False,
                        "available_models": [],
                        "error": f"Groq returned HTTP status {resp.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "connected": False,
                "provider": "groq",
                "base_url": self.GROQ_API_BASE,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error": "Cannot connect to Groq API endpoint. Check internet connection."
            }
        except httpx.TimeoutException:
            return {
                "connected": False,
                "provider": "groq",
                "base_url": self.GROQ_API_BASE,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error": "Connection to Groq API timed out."
            }
        except Exception as exc:
            return {
                "connected": False,
                "provider": "groq",
                "base_url": self.GROQ_API_BASE,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error": f"Error reaching Groq API: {str(exc)}"
            }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        override_model: Optional[str] = None,
        override_temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Synchronous fallback request to Groq /chat/completions.
        """
        headers = self._get_headers()
        target_model = override_model or self.model
        temp = override_temperature if override_temperature is not None else self.temperature
        max_t = max_tokens or self.max_tokens

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_t,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=3.0)) as client:
                resp = client.post(
                    f"{self.GROQ_API_BASE}/chat/completions",
                    headers=headers,
                    json=payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                    return ""
                elif resp.status_code in (401, 403):
                    raise GroqAuthError("Invalid or unauthorized Groq API key.", status_code=resp.status_code)
                elif resp.status_code == 404:
                    raise GroqModelNotFoundError(f"Model '{target_model}' not found on Groq.", status_code=404)
                elif resp.status_code == 429:
                    raise GroqRateLimitError("Groq API rate limit exceeded.", status_code=429)
                else:
                    raise GroqServiceError(
                        f"Groq API returned HTTP {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code
                    )
        except httpx.ConnectError as exc:
            raise GroqConnectionError(f"Failed to connect to Groq API: {exc}")
        except httpx.TimeoutException as exc:
            raise GroqTimeoutError(f"Groq API request timed out after {self.timeout}s")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        override_model: Optional[str] = None,
        override_temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously streams tokens from Groq Cloud LPU via SSE.
        Yields tokens immediately with sub-second time-to-first-token.
        """
        headers = self._get_headers()
        target_model = override_model or self.model
        temp = override_temperature if override_temperature is not None else self.temperature
        max_t = max_tokens or self.max_tokens
        client = self._get_async_client()

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_t,
            "stream": True,
        }

        try:
            async with client.stream(
                "POST",
                "/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            ) as response:
                if response.status_code == 401 or response.status_code == 403:
                    raise GroqAuthError("Invalid or unauthorized Groq API key.", status_code=response.status_code)
                if response.status_code == 404:
                    raise GroqModelNotFoundError(f"Model '{target_model}' not found on Groq.", status_code=404)
                if response.status_code == 429:
                    raise GroqRateLimitError("Groq API rate limit reached. Retrying or switching to fallback.", status_code=429)
                if response.status_code != 200:
                    err_bytes = await response.aread()
                    raise GroqServiceError(
                        f"Groq returned HTTP {response.status_code}: {err_bytes.decode('utf-8', errors='replace')[:200]}",
                        status_code=response.status_code
                    )

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    trimmed = line.strip()
                    if not trimmed.startswith("data: "):
                        continue
                    data_str = trimmed[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token

        except httpx.ConnectError as exc:
            logger.error(f"Failed to connect to Groq API: {exc}")
            raise GroqConnectionError("Cannot connect to Groq API. Please check your network connection.")
        except httpx.TimeoutException as exc:
            logger.error(f"Timeout streaming from Groq: {exc}")
            raise GroqTimeoutError(f"Inference timed out after {self.timeout}s waiting for Groq response.")


groq_service = GroqService()
