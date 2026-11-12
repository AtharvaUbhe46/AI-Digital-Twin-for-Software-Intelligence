import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx

from app.core.config import settings

logger = logging.getLogger("digital_twin.assistant.ollama")


class OllamaServiceError(Exception):
    """Base exception for Ollama interactions."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class OllamaConnectionError(OllamaServiceError):
    """Raised when Ollama server cannot be reached."""
    pass


class OllamaModelNotFoundError(OllamaServiceError):
    """Raised when the configured model is not found in local Ollama."""
    pass


class OllamaTimeoutError(OllamaServiceError):
    """Raised when Ollama request exceeds timeout limit."""
    pass


class OllamaService:
    """
    High-performance client abstraction for interacting with the local Ollama instance running Qwen.
    Supports asynchronous streaming (SSE), connection pooling, intelligent model resolution,
    and granular health verification.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        self.temperature = temperature if temperature is not None else settings.OLLAMA_TEMPERATURE
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_async_client(self) -> httpx.AsyncClient:
        """
        Returns a persistent AsyncClient with HTTP connection pooling and keep-alive.
        """
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=6.0),
                limits=httpx.Limits(max_keepalive_connections=8, max_connections=16, keepalive_expiry=30.0),
            )
        return self._async_client

    async def aclose(self):
        """Closes the underlying persistent HTTP client pool."""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None

    def resolve_model_sync(self, target_model: Optional[str] = None) -> str:
        """
        Dynamically verifies whether the target model is installed in Ollama.
        If not found, searches for any installed Qwen variant (e.g. qwen2.5:3b, qwen2.5:7b)
        or falls back to the first locally installed model.
        """
        req_model = target_model or self.model
        url = f"{self.base_url}/api/tags"
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    installed = [m.get("name", "") for m in resp.json().get("models", [])]
                    if req_model in installed:
                        return req_model
                    # Check partial matches (e.g., prefix or contains)
                    for m in installed:
                        if m.startswith(req_model) or req_model.split(":")[0] in m:
                            return m
                    # Check any Qwen models
                    qwen_models = [m for m in installed if "qwen" in m.lower()]
                    if qwen_models:
                        return qwen_models[0]
                    if installed:
                        return installed[0]
        except Exception:
            pass
        return req_model

    async def resolve_model_async(self, target_model: Optional[str] = None) -> str:
        """Asynchronous version of model resolution."""
        req_model = target_model or self.model
        client = self._get_async_client()
        try:
            resp = await client.get("/api/tags", timeout=3.0)
            if resp.status_code == 200:
                installed = [m.get("name", "") for m in resp.json().get("models", [])]
                if req_model in installed:
                    return req_model
                for m in installed:
                    if m.startswith(req_model) or req_model.split(":")[0] in m:
                        return m
                qwen_models = [m for m in installed if "qwen" in m.lower()]
                if qwen_models:
                    return qwen_models[0]
                if installed:
                    return installed[0]
        except Exception:
            pass
        return req_model

    async def warmup_model(self) -> None:
        """
        Pre-warms the local Qwen model into memory with keep_alive='60m'
        so user queries experience zero cold-start latency.
        """
        try:
            target_model = await self.resolve_model_async(self.model)
            client = self._get_async_client()
            await client.post(
                "/api/generate",
                json={
                    "model": target_model,
                    "prompt": "",
                    "keep_alive": "60m"
                },
                timeout=15.0
            )
            logger.info(f"Ollama Qwen model '{target_model}' pre-warmed and resident in memory.")
        except Exception as e:
            logger.debug(f"Ollama warmup skipped: {e}")

    def check_health(self) -> Dict[str, Any]:
        """
        Pings Ollama `/api/tags` to verify connectivity and check if the configured
        Qwen model is pulled and available locally.
        """
        url = f"{self.base_url}/api/tags"
        try:
            with httpx.Client(timeout=4.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    model_found = any(
                        self.model == m or self.model in m or m.startswith(self.model.split(":")[0])
                        for m in models
                    )
                    # If any Qwen model is available, mark as available with active alias
                    resolved = self.resolve_model_sync(self.model)
                    has_any_qwen = any("qwen" in m.lower() for m in models)

                    return {
                        "connected": True,
                        "base_url": self.base_url,
                        "model": self.model,
                        "active_model": resolved,
                        "model_available": model_found or has_any_qwen,
                        "available_models": models,
                        "error": None if (model_found or has_any_qwen) else f"Configured model '{self.model}' is not installed in Ollama. Run 'ollama pull {self.model}' to download it."
                    }
                else:
                    return {
                        "connected": False,
                        "base_url": self.base_url,
                        "model": self.model,
                        "active_model": None,
                        "model_available": False,
                        "available_models": [],
                        "error": f"Ollama returned HTTP status {response.status_code}: {response.text[:200]}"
                    }
        except httpx.ConnectError:
            return {
                "connected": False,
                "base_url": self.base_url,
                "model": self.model,
                "active_model": None,
                "model_available": False,
                "available_models": [],
                "error": f"Cannot connect to Ollama at {self.base_url}. Make sure Ollama is installed and running (`ollama serve`)."
            }
        except httpx.TimeoutException:
            return {
                "connected": False,
                "base_url": self.base_url,
                "model": self.model,
                "active_model": None,
                "model_available": False,
                "available_models": [],
                "error": f"Connection to Ollama timed out at {self.base_url}."
            }
        except Exception as exc:
            return {
                "connected": False,
                "base_url": self.base_url,
                "model": self.model,
                "active_model": None,
                "model_available": False,
                "available_models": [],
                "error": f"Error connecting to Ollama: {str(exc)}"
            }

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        override_model: Optional[str] = None,
        override_temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously streams generated tokens from Ollama `/api/chat` using persistent connection pooling.
        Yields individual token strings in real time as they arrive.
        """
        client = self._get_async_client()
        target_model = await self.resolve_model_async(override_model or self.model)
        temp = override_temperature if override_temperature is not None else self.temperature

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "keep_alive": "60m",
            "options": {
                "num_ctx": 1536,
                "num_thread": 6,
                "num_predict": 350,
                "temperature": temp,
                "top_p": 0.9,
            }
        }

        try:
            async with client.stream("POST", "/api/chat", json=payload, timeout=self.timeout) as response:
                if response.status_code == 404:
                    raise OllamaModelNotFoundError(
                        f"Model '{target_model}' not found in local Ollama. Please run: 'ollama pull {target_model}'"
                    )
                if response.status_code != 200:
                    err_text = await response.aread()
                    raise OllamaServiceError(
                        f"Ollama returned HTTP {response.status_code}: {err_text.decode('utf-8', errors='replace')[:200]}",
                        status_code=response.status_code
                    )

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message", {})
                    token = msg.get("content", "")
                    if token:
                        yield token

                    if chunk.get("done", False):
                        break

        except httpx.ConnectError as exc:
            logger.error(f"Failed to connect to Ollama at {self.base_url}: {exc}")
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure `ollama serve` is running."
            )
        except httpx.TimeoutException as exc:
            logger.error(f"Timeout streaming from Ollama: {exc}")
            raise OllamaTimeoutError(
                f"Inference timed out after {self.timeout}s waiting for local Qwen response."
            )
        except (OllamaConnectionError, OllamaModelNotFoundError, OllamaTimeoutError, OllamaServiceError):
            raise
        except Exception as exc:
            logger.error(f"Unexpected streaming error with Ollama: {exc}", exc_info=True)
            raise OllamaServiceError(f"Streaming error with local AI model: {str(exc)}")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        override_model: Optional[str] = None,
        override_temperature: Optional[float] = None,
    ) -> str:
        """
        Synchronous chat completion for non-streaming callers and unit tests.
        """
        target_model = self.resolve_model_sync(override_model or self.model)
        temp = override_temperature if override_temperature is not None else self.temperature
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "keep_alive": "60m",
            "options": {
                "num_ctx": 1536,
                "num_thread": 6,
                "num_predict": 350,
                "temperature": temp,
                "top_p": 0.9,
            }
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)

            if response.status_code == 200:
                result = response.json()
                msg = result.get("message", {})
                content = msg.get("content", "").strip()
                if not content:
                    raise OllamaServiceError("Ollama returned an empty response.")
                return content

            elif response.status_code == 404:
                raise OllamaModelNotFoundError(
                    f"Model '{target_model}' not found in local Ollama. Please run: 'ollama pull {target_model}'"
                )
            else:
                error_body = response.text[:300]
                raise OllamaServiceError(
                    f"Ollama returned HTTP {response.status_code}: {error_body}",
                    status_code=response.status_code
                )

        except httpx.ConnectError as exc:
            logger.error(f"Failed to connect to Ollama at {url}: {exc}")
            raise OllamaConnectionError(
                f"I couldn't connect to the local Qwen model. Make sure Ollama is running at {self.base_url} and the configured Qwen model ({target_model}) is available."
            )
        except httpx.TimeoutException as exc:
            logger.error(f"Timeout waiting for Ollama response from {url}: {exc}")
            raise OllamaServiceError(
                f"Request to local Qwen model timed out after {self.timeout}s. The model may be loading into memory or the machine is under heavy load."
            )
        except (OllamaConnectionError, OllamaModelNotFoundError, OllamaServiceError):
            raise
        except Exception as exc:
            logger.error(f"Unexpected error communicating with Ollama: {exc}", exc_info=True)
            raise OllamaServiceError(f"Error communicating with local AI model: {str(exc)}")


ollama_service = OllamaService()
