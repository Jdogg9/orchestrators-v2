from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from src.llm_types import LLMResponse


@dataclass
class ProviderConfig:
    base_url: str
    model: str
    timeout_sec: int
    health_timeout_sec: int
    max_output_chars: int
    retry_count: int
    retry_backoff_sec: float
    circuit_max_failures: int
    circuit_reset_sec: int
    network_enabled: bool
    model_allowlist: Optional[set[str]]


class CircuitBreaker:
    def __init__(self, max_failures: int, reset_sec: int) -> None:
        self.max_failures = max_failures
        self.reset_sec = reset_sec
        self.failures = 0
        self.opened_at: Optional[float] = None

    def allow(self) -> bool:
        if self.failures < self.max_failures:
            return True
        if self.opened_at is None:
            self.opened_at = time.time()
            return False
        if (time.time() - self.opened_at) >= self.reset_sec:
            self.failures = 0
            self.opened_at = None
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.max_failures and self.opened_at is None:
            self.opened_at = time.time()


class OllamaProvider:
    """Hardened Ollama provider using /api/chat."""

    provider_name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.config = ProviderConfig(
            base_url=base_url or os.getenv("ORCH_OLLAMA_URL", "http://127.0.0.1:11434"),
            model=model or os.getenv("ORCH_MODEL_CHAT", "qwen2.5:3b"),
            timeout_sec=int(os.getenv("ORCH_LLM_TIMEOUT_SEC", "30")),
            health_timeout_sec=int(os.getenv("ORCH_LLM_HEALTH_TIMEOUT_SEC", "5")),
            max_output_chars=int(os.getenv("ORCH_LLM_MAX_OUTPUT_CHARS", "4000")),
            retry_count=int(os.getenv("ORCH_LLM_RETRY_COUNT", "0")),
            retry_backoff_sec=float(os.getenv("ORCH_LLM_RETRY_BACKOFF_SEC", "0.5")),
            circuit_max_failures=int(os.getenv("ORCH_LLM_CIRCUIT_MAX_FAILURES", "3")),
            circuit_reset_sec=int(os.getenv("ORCH_LLM_CIRCUIT_RESET_SEC", "30")),
            network_enabled=os.getenv("ORCH_LLM_NETWORK_ENABLED", "0") == "1",
            model_allowlist=self._parse_allowlist(os.getenv("ORCH_LLM_MODEL_ALLOWLIST", "")),
        )
        self._breaker = CircuitBreaker(
            max_failures=self.config.circuit_max_failures,
            reset_sec=self.config.circuit_reset_sec,
        )
        self._ensure_model_allowed(self.config.model)

    @staticmethod
    def _parse_allowlist(value: str) -> Optional[set[str]]:
        if not value:
            return None
        allowlist = {item.strip() for item in value.split(",") if item.strip()}
        return allowlist or None

    def _ensure_network_allowed(self) -> None:
        if not self.config.network_enabled:
            raise RuntimeError("network_disabled: set ORCH_LLM_NETWORK_ENABLED=1 to allow provider calls")

    def _ensure_model_allowed(self, model: str) -> None:
        if self.config.model_allowlist and model not in self.config.model_allowlist:
            raise ValueError(f"model_not_allowlisted:{model}")

    def _cap_output(self, content: str) -> tuple[str, bool]:
        if self.config.max_output_chars <= 0:
            return content, False
        if len(content) <= self.config.max_output_chars:
            return content, False
        return content[: self.config.max_output_chars], True

    def _request_with_retries(self, messages: List[Dict[str, str]]) -> tuple[Dict[str, Any], int]:
        attempts = 0
        last_exc: Optional[Exception] = None

        for attempt in range(self.config.retry_count + 1):
            attempts = attempt + 1
            try:
                resp = requests.post(
                    f"{self.config.base_url}/api/chat",
                    json={"model": self.config.model, "messages": messages, "stream": False},
                    timeout=self.config.timeout_sec,
                )
                resp.raise_for_status()
                data = resp.json()
                return data, attempts
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.config.retry_count:
                    time.sleep(self.config.retry_backoff_sec)

        raise RuntimeError(f"provider_request_failed:{last_exc}")

    def generate(self, messages: List[Dict[str, str]]) -> LLMResponse:
        self._ensure_network_allowed()
        if not self._breaker.allow():
            raise RuntimeError("circuit_open: provider temporarily unavailable")

        start = time.time()
        try:
            data, attempts = self._request_with_retries(messages)
            content = data.get("message", {}).get("content", "")
            capped, truncated = self._cap_output(content)
            if truncated:
                data = dict(data)
                data["truncated"] = True
                data["max_output_chars"] = self.config.max_output_chars
            latency_ms = int((time.time() - start) * 1000)
            self._breaker.record_success()
            return LLMResponse(
                content=capped,
                model=self.config.model,
                raw=data,
                provider=self.provider_name,
                latency_ms=latency_ms,
                attempts=attempts,
                truncated=truncated,
            )
        except Exception:
            self._breaker.record_failure()
            raise

    def health_check(self) -> tuple[bool, str]:
        if not self.config.network_enabled:
            return False, "network_disabled"
        if not self._breaker.allow():
            return False, "circuit_open"
        try:
            resp = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=self.config.health_timeout_sec,
            )
            if resp.status_code != 200:
                return False, f"ollama status {resp.status_code}"
            return True, "ok"
        except requests.RequestException as exc:
            self._breaker.record_failure()
            return False, f"ollama error: {exc}"