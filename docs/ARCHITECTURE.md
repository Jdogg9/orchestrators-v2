# Architecture (ORCHESTRATORS_V2)

## Layers

1. API layer (server)
2. Orchestrator (routing + governance hooks)
3. Tokenizer layer (ORCH_TOKENIZER)
4. Tools (pluggable functions)
5. Optional persistence (memory/recall) behind flags

## ORCH_TOKENIZER Layer (Graceful Degradation)

Token-aware orchestration relies on the local **ORCH_TOKENIZER** package to provide
deterministic token counts for routing and pruning. When the tokenizer dependency
is unavailable, the system falls back to **byte-level tokenization** so the safety
logic continues to run without hard failures. This preserves guardrails like tiered
reasoning and priority-aware pruning while clearly signaling a degraded mode.

## Memory Governance (Optional)

Memory capture is **off by default** and gated by explicit policy:

- `ORCH_MEMORY_ENABLED=1` enables memory system.
- `ORCH_MEMORY_CAPTURE_ENABLED=1` allows candidate capture.
- `ORCH_MEMORY_WRITE_POLICY` controls capture mode (`off|strict|capture_only`).

Every capture attempt emits a **decision trace** with a strict taxonomy:

- allow:explicit_intent
- allow:dedupe_update
- allow:capture_only
- deny:feature_disabled
- deny:policy_write_disabled
- deny:no_explicit_intent
- deny:scrubbed_too_short
- deny:sensitive_content
- deny:error

Decision traces are persisted in a local SQLite trace store when `ORCH_TRACE_ENABLED=1`.

## Design goals

* Reproducible
* Local-first
* Safe defaults
* Extensible without refactoring core
