# LLM Provider Contract

This document defines the minimal contract for `llm_provider` implementations and how to integrate safely.

## Contract Summary

Provider implementations must:

- Accept a list of chat `messages` (OpenAI format)
- Return an `LLMResponse` with:
  - `content` (string)
  - `model` (string)
  - `provider` (string)
  - `latency_ms` (int)
  - `attempts` (int)
  - `truncated` (bool)

LLMs are **disabled by default**. Enable explicitly and pass readiness checks.

## Core Files

- `src/llm_provider.py` — provider selection
- `src/ollama_provider.py` — hardened Ollama implementation
- `src/llm_types.py` — response schema
- `tests/test_llm_provider_contract.py` — contract tests

## Required Behaviors

### 1) Network gating

Providers must respect `ORCH_LLM_NETWORK_ENABLED=1` before any outbound calls.

### 2) Timeouts + retries

Providers must enforce timeouts and (if configured) retry with backoff:
- `ORCH_LLM_TIMEOUT_SEC`
- `ORCH_LLM_RETRY_COUNT`
- `ORCH_LLM_RETRY_BACKOFF_SEC`

### 3) Output caps

Responses must be capped using:
- `ORCH_LLM_MAX_OUTPUT_CHARS`

If truncated, return `truncated=true`.

### 4) Circuit breaker

Providers must stop calling out when failures exceed:
- `ORCH_LLM_CIRCUIT_MAX_FAILURES`

And resume after:
- `ORCH_LLM_CIRCUIT_RESET_SEC`

### 5) Allowlist (optional)

Use `ORCH_LLM_MODEL_ALLOWLIST` to permit specific model IDs only.

## Example Provider Stub

```python
from src.llm_types import LLMResponse

class StubProvider:
    def generate(self, messages):
        return LLMResponse(
            content="stub response",
            model="stub",
            provider="stub",
            latency_ms=1,
            attempts=1,
            truncated=False,
        )
```

## Enabling LLMs Safely

Follow:
- [LLM Enablement Checklist](LLM_ENABLEMENT_CHECKLIST.md)

## Related Docs

- [Production Readiness](PRODUCTION_READINESS.md)
- [Observability Stack](OBSERVABILITY_STACK.md)
