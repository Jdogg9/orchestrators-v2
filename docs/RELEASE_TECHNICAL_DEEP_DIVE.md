# Release Technical Deep-Dive — Transparency & Traceability

## Summary
This release adds protocol-level transparency, trace-level confidence signaling, and machine-readable governance exports to support audit readiness and automated compliance workflows.

## Protocol-Level Transparency (X-AI-Generated)
All API responses include the header:

- `X-AI-Generated: true`

This enforces disclosure at the protocol layer rather than relying on UI tooling or client behavior. It is intended to satisfy the transparency requirements in EU AI Act Article 50 for AI-generated content.

## Summary Confidence Warning (Trace Signal)
Summaries generated during token budget pruning now emit an explicit trace warning when confidence is low:

- Step type: `summary_confidence_warning`
- Trigger: `summary_confidence_score < 0.7`
- Fields: `summary_confidence_score`, `threshold`, `pinned_keywords_total`, `pinned_keywords_matched`

This gives auditors and SREs a deterministic signal that the summary may require additional review.

## NIST AI RMF Measure 2.1 Mapping (JSON-LD Export)
The compliance JSON-LD export now explicitly maps token utilization metrics to NIST AI RMF Measure 2.1. Evidence includes:

- `orch.token.utilization_ratio`
- `orch.token.pruned_input_tokens`
- `orch.token.pruned_messages`
- `orch.token.pruned_turns`

This enables automated ingestion by GRC systems and links runtime evidence to the Measure function.

## Files Updated
- src/orchestrator.py — added `summary_confidence_warning` trace step
- src/server.py — `X-AI-Generated: true` response header (already integrated)
- scripts/generate_compliance_report.py — Measure 2.1 JSON-LD mapping
- docs/LETTER_TO_CISO.md — explicit protocol-level transparency language

## Operational Notes
- The warning step is emitted only when summaries are added and tracing is enabled.
- The transparency header is emitted for every API response, independent of streaming mode.
- Reports remain in reports/ and are ignored in version control.
