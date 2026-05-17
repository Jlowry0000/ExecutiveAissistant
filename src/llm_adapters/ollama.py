import os
import httpx
from .base import LLMAdapter


class OllamaAdapter(LLMAdapter):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        **kwargs
    ):
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def complete(
        self,
        messages: list[dict[str, str]],
        json_output: bool = False,
        **kwargs
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.2),
            }
        }
        if json_output:
            payload["format"] = "json"

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()["message"]["content"]