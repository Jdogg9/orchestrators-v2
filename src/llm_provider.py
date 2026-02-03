from __future__ import annotations

from typing import Dict, List
import os

from src.llm_types import LLMResponse
from src.ollama_provider import OllamaProvider


class LLMProvider:
    def generate(self, messages: List[Dict[str, str]]) -> LLMResponse:  # pragma: no cover - interface
        raise NotImplementedError

    def health_check(self) -> tuple[bool, str]:  # pragma: no cover - interface
        return False, "health_check not implemented"


def get_provider(model_override: str | None = None) -> LLMProvider:
    provider = os.getenv("ORCH_LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        return OllamaProvider(model=model_override)
    raise ValueError(f"Unsupported LLM provider: {provider}")
