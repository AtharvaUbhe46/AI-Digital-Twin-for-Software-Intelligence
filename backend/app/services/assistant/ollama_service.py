import logging
from typing import Dict, Any, List, Optional
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


class OllamaService:
    """
    Dedicated client abstraction for interacting with local Ollama instance running Qwen.
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
                    # Check exact match or base name (e.g. qwen2.5:7b matches qwen2.5:7b-instruct)
                    model_found = any(
                        self.model == m or self.model in m or m.startswith(self.model.split(":")[0])
                        for m in models
                    )
                    return {
                        "connected": True,
                        "base_url": self.base_url,
                        "model": self.model,
                        "model_available": model_found,
                        "available_models": models,
                        "error": None if model_found else f"Configured model '{self.model}' is not installed in Ollama. Run 'ollama pull {self.model}' to download it."
                    }
                else:
                    return {
                        "connected": False,
                        "base_url": self.base_url,
                        "model": self.model,
                        "model_available": False,
                        "available_models": [],
                        "error": f"Ollama returned HTTP status {response.status_code}: {response.text[:200]}"
                    }
        except httpx.ConnectError:
            return {
                "connected": False,
                "base_url": self.base_url,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error": f"Cannot connect to Ollama at {self.base_url}. Make sure Ollama is installed and running (`ollama serve`)."
            }
        except httpx.TimeoutException:
            return {
                "connected": False,
                "base_url": self.base_url,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error": f"Connection to Ollama timed out at {self.base_url}."
            }
        except Exception as exc:
            return {
                "connected": False,
                "base_url": self.base_url,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error": f"Error connecting to Ollama: {str(exc)}"
            }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        override_model: Optional[str] = None,
        override_temperature: Optional[float] = None,
    ) -> str:
        """
        Sends conversation messages to Ollama `/api/chat` and returns the generated text answer.
        """
        target_model = override_model or self.model
        temp = override_temperature if override_temperature is not None else self.temperature
        url = f"{self.base_url}/api/chat"

        # Intelligently resolve model: if target_model is not installed, but an alternative Qwen model is available, use it
        resolved_model = target_model
        try:
            with httpx.Client(timeout=3.0) as check_client:
                tag_resp = check_client.get(f"{self.base_url}/api/tags")
                if tag_resp.status_code == 200:
                    installed = [m.get("name", "") for m in tag_resp.json().get("models", [])]
                    if target_model not in installed:
                        # Find closest matching qwen model or first installed model
                        qwen_matches = [m for m in installed if "qwen" in m.lower()]
                        if qwen_matches:
                            resolved_model = qwen_matches[0]
                            logger.info(f"Target model '{target_model}' not found; resolving to installed '{resolved_model}'")
                        elif installed:
                            resolved_model = installed[0]
        except Exception:
            pass

        payload = {
            "model": resolved_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temp,
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
