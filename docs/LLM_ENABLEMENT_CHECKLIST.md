# LLM Enablement Checklist (Safe-by-Default)

ORCHESTRATORS_V2 ships with LLMs **OFF** by default. If you enable LLMs, use this checklist and run the verification script to ensure guardrails are active.

## ✅ Required Settings (when `ORCH_LLM_ENABLED=1`)

- `ORCH_LLM_NETWORK_ENABLED=1`
  - Explicit opt-in to provider calls.
- `ORCH_LLM_PROVIDER` set (default: `ollama`).
- Provider URL configured (e.g., `ORCH_OLLAMA_URL`).
- Timeouts set:
  - `ORCH_LLM_TIMEOUT_SEC`
  - `ORCH_LLM_HEALTH_TIMEOUT_SEC`
- Output caps set:
  - `ORCH_LLM_MAX_OUTPUT_CHARS`
- Retry + circuit breaker set:
  - `ORCH_LLM_RETRY_COUNT`
  - `ORCH_LLM_RETRY_BACKOFF_SEC`
  - `ORCH_LLM_CIRCUIT_MAX_FAILURES`
  - `ORCH_LLM_CIRCUIT_RESET_SEC`
- Receipts enabled:
  - `ORCH_TRACE_ENABLED=1`

Optional hardening:
- `ORCH_LLM_MODEL_ALLOWLIST` (comma-separated list of approved models)

## 📎 References

- [LLM Provider Contract](LLM_PROVIDER_CONTRACT.md)
- [Tool Approval Contract](TOOL_APPROVAL_CONTRACT.md)

## 🔍 Verification Script

```bash
./scripts/verify_llm_enablement.sh
```

This script **fails fast** if any required knobs are missing or unsafe defaults are detected.

## 🧪 Demo Mode (No LLMs)

When `ORCH_LLM_ENABLED=0`, the API serves a deterministic **demo response** that:

- shows the intent/route heuristics,
- explains approval gates,
- and avoids any network calls.

This lets users validate the architecture offline before enabling LLMs.