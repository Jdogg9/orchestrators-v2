# Architecture (ORCHESTRATORS_V2)

## Layers

1. API layer (server)
2. Orchestrator (routing + governance hooks)
3. Tools (pluggable functions)
4. Optional persistence (memory/recall) behind flags

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
