from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import os
import requests


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    raw: Dict[str, Any]


class LLMProvider:
    def generate(self, messages: List[Dict[str, str]]) -> LLMResponse:  # pragma: no cover - interface
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """Minimal Ollama provider using /api/chat."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = base_url or os.getenv("ORCH_OLLAMA_URL", "http://127.0.0.1:11434")
        self.model = model or os.getenv("ORCH_MODEL_CHAT", "qwen2.5:3b")

    def generate(self, messages: List[Dict[str, str]]) -> LLMResponse:
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return LLMResponse(content=content, model=self.model, raw=data)


def get_provider() -> LLMProvider:
    provider = os.getenv("ORCH_LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unsupported LLM provider: {provider}")
