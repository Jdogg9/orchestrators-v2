# Compliance Story (Artifact-First)

**Not legal advice.** This document explains how Orchestrators-v2 supports compliance-oriented workflows through local-first defaults, receipts, and boundary checks.

## What Gets Logged (and What Does Not)

**Logged (receipts):**
- Trace receipts (route decisions, tool execution status, and high-level metadata)
- Policy decisions (when enabled via `ORCH_TOOL_POLICY_ENFORCE`)
- Optional OpenTelemetry IDs when `ORCH_OTEL_ENABLED=1`

**Not logged (by default):**
- Raw secrets (keys/tokens) — scrubbed by tool output guardrails
- Full prompt bodies outside of explicit tool payloads
- Any cloud-side telemetry (local-first defaults)

## How Audit Receipts Work

- Receipts are stored locally in a trace database (default: `instance/trace.db`).
- Each receipt contains minimal metadata for auditability without full content leakage.
- Scripts such as [scripts/verify_public_boundary.sh](../scripts/verify_public_boundary.sh) ensure runtime state is not published.

**Auditability principle (token telemetry):** every AI decision is now receipt-backed
with exact token-density data (input/output/utilization), enabling transparent resource
management and forensic review without storing raw prompts.

## Operating Offline / Air-Gapped

- Set `ORCH_LLM_ENABLED=0` to disable external model calls.
- Keep `ORCH_TOOL_WEB_SEARCH_ENABLED=0` for zero network usage.
- Run the API locally and restrict outbound network at the host firewall.

## Mapping (Not Legal Advice)

| Framework | How Orchestrators-v2 Helps | Boundary Notes |
| --- | --- | --- |
| GDPR | Data minimization by default, local-only receipts, deletion is local-only | You must define retention and deletion policy for local traces. |
| HIPAA | Local-only processing, audit trail capability, optional auth gates | You must configure access control and secure storage. |
| SOC 2 | Change tracking via git + receipts, least privilege defaults | You must enforce approvals, access controls, and monitoring. |

## Token-Aware Pruning & Safety Audits

Token-aware pruning provides a **deterministic, auditable** control for managing
context growth without sacrificing the initial intent of a conversation. This aligns
with AI safety expectations in both EU and US frameworks by enforcing:

- **Data minimization**: middle-turn pruning reduces unnecessary retention of context.
- **Goal preservation**: system prompts and initial goals remain pinned.
- **Transparent receipts**: token usage (input/output/utilization) is recorded in trace steps.
- **Deterministic behavior**: pruning decisions are rule-based, not probabilistic.

### EU AI Act (Risk Management)

Token-aware pruning supports risk controls by limiting the context window and
documenting the decision path (trace receipts). This helps demonstrate:

- predictable execution behavior,
- bounded memory usage, and
- configurable safeguards (tiered thresholds).

### US AI RMF / NIST AI Risk Management Framework

Token usage telemetry and deterministic pruning provide measurable evidence
for governance and oversight. Operators can audit:

- context utilization over time,
- adherence to token budgets,
- and whether summary mode was triggered.

**Bottom line:** token-aware pruning makes the system’s memory management
explicit, inspectable, and defensible during external audits.

## What You Must Configure to Be Compliant

- **Access control**: `ORCH_REQUIRE_BEARER=1` and a strong bearer token.
- **Receipt retention**: define a retention policy for `instance/trace.db`.
- **Secure storage**: ensure trace DB and logs are on encrypted disks if required.
- **Network policy**: disable external tools or enforce outbound restrictions.

## Honest Boundaries

- Orchestrators-v2 does **not** provide certified compliance.
- This is a framework with safety-first defaults and auditable receipts.
- You own the operational controls, retention, and access policies.
