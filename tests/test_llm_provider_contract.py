import os

import pytest
import requests

from src.llm_types import LLMResponse
from src.ollama_provider import OllamaProvider


class DummyResponse:
    def __init__(self, content: str, status_code: int = 200):
        self._content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self):
        return {"message": {"content": self._content}}


def test_offline_mode_blocks_network(monkeypatch):
    monkeypatch.setenv("ORCH_LLM_NETWORK_ENABLED", "0")
    monkeypatch.setenv("ORCH_LLM_ENABLED", "1")

    def _no_call(*_args, **_kwargs):
        raise AssertionError("network should not be called when ORCH_LLM_NETWORK_ENABLED=0")

    monkeypatch.setattr("requests.post", _no_call)
    provider = OllamaProvider()

    with pytest.raises(RuntimeError, match="network_disabled"):
        provider.generate([{"role": "user", "content": "hi"}])


def test_provider_caps_output(monkeypatch):
    monkeypatch.setenv("ORCH_LLM_NETWORK_ENABLED", "1")
    monkeypatch.setenv("ORCH_LLM_MAX_OUTPUT_CHARS", "5")

    def _fake_post(*_args, **_kwargs):
        return DummyResponse("0123456789")

    monkeypatch.setattr("requests.post", _fake_post)
    provider = OllamaProvider()
    result = provider.generate([{"role": "user", "content": "hi"}])

    assert len(result.content) == 5
    assert result.truncated is True


def test_provider_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("ORCH_LLM_NETWORK_ENABLED", "1")
    monkeypatch.setenv("ORCH_LLM_RETRY_COUNT", "1")
    monkeypatch.setenv("ORCH_LLM_RETRY_BACKOFF_SEC", "0")
    calls = {"count": 0}

    def _flaky_post(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.RequestException("temporary failure")
        return DummyResponse("ok")

    monkeypatch.setattr("requests.post", _flaky_post)
    provider = OllamaProvider()
    result = provider.generate([{"role": "user", "content": "hi"}])

    assert result.content == "ok"
    assert result.attempts == 2


def test_llm_calls_are_receipted(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCH_LLM_ENABLED", "1")
    monkeypatch.setenv("ORCH_LLM_NETWORK_ENABLED", "1")
    monkeypatch.setenv("ORCH_TRACE_ENABLED", "1")
    monkeypatch.setenv("ORCH_TRACE_DB_PATH", str(tmp_path / "trace.db"))

    from src import tracer as tracer_module
    tracer_module._tracer = None

    class FakeProvider:
        def generate(self, messages):
            return LLMResponse(
                content="ok",
                model="fake",
                raw={},
                provider="fake",
                latency_ms=1,
                attempts=1,
                truncated=False,
            )

    monkeypatch.setattr("src.orchestrator.get_provider", lambda model_override=None: FakeProvider())

    from src.orchestrator import Orchestrator

    tracer = tracer_module.get_tracer()
    handle = tracer.start_trace({"route": "test"})

    orch = Orchestrator()
    orch.handle([{"role": "user", "content": "hi"}], trace_id=handle.trace_id)

    steps = tracer.get_trace_steps(handle.trace_id)
    assert any(step["step_type"] == "llm_provider" for step in steps)