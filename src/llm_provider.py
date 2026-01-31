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

    def health_check(self) -> tuple[bool, str]:  # pragma: no cover - interface
        return False, "health_check not implemented"


class OllamaProvider(LLMProvider):
    """Minimal Ollama provider using /api/chat."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = base_url or os.getenv("ORCH_OLLAMA_URL", "http://127.0.0.1:11434")
        self.model = model or os.getenv("ORCH_MODEL_CHAT", "qwen2.5:3b")
        self.timeout = int(os.getenv("ORCH_LLM_TIMEOUT_SEC", "30"))
        self.health_timeout = int(os.getenv("ORCH_LLM_HEALTH_TIMEOUT_SEC", "5"))

    def generate(self, messages: List[Dict[str, str]]) -> LLMResponse:
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return LLMResponse(content=content, model=self.model, raw=data)

    def health_check(self) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=self.health_timeout)
            if resp.status_code != 200:
                return False, f"ollama status {resp.status_code}"
            return True, "ok"
        except requests.RequestException as exc:
            return False, f"ollama error: {exc}"


def get_provider(model_override: str | None = None) -> LLMProvider:
    provider = os.getenv("ORCH_LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        return OllamaProvider(model=model_override)
    raise ValueError(f"Unsupported LLM provider: {provider}")
