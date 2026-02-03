# Memory & RAG (Optional)

Memory is **disabled by default** and governed by explicit policies. This module is opt-in and designed for auditability.

## Flags

- `ORCH_MEMORY_ENABLED` (default: 0)
- `ORCH_MEMORY_CAPTURE_ENABLED` (default: 0)
- `ORCH_MEMORY_WRITE_POLICY` (default: off)
- `ORCH_MEMORY_CAPTURE_TTL_MINUTES` (default: 180)
- `ORCH_MEMORY_DB_PATH` (default: instance/orchestrator_core.db)
- `ORCH_MEMORY_SCRUB_REDACT_PII` (default: 1)

## Write Policy Modes

- `off`: no writes
- `strict`: only explicit user intent ("remember this")
- `capture_only`: capture candidates only (no promotion)

## Decision Taxonomy

The memory pipeline emits decision reasons such as:

- `allow:explicit_intent`
- `allow:dedupe_update`
- `allow:capture_only`
- `deny:feature_disabled`
- `deny:policy_write_disabled`
- `deny:no_explicit_intent`
- `deny:scrubbed_too_short`
- `deny:sensitive_content`
- `deny:error`

## Storage

- Table: `memory_candidates`
- TTL: `ORCH_MEMORY_CAPTURE_TTL_MINUTES`
- Scrubbing: redacts secrets and PII when `ORCH_MEMORY_SCRUB_REDACT_PII=1`

## Threat Model Notes

- Memory is **opt-in** and must be explicitly enabled.
- Scrubbing reduces leak risk for accidental capture.
- TTL prevents indefinite retention by default.

## Related Docs

- [Threat Model](THREAT_MODEL.md)
- [Operator Contract](OPERATOR_CONTRACT.md)
