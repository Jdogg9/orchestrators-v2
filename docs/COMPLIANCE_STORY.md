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

## What You Must Configure to Be Compliant

- **Access control**: `ORCH_REQUIRE_BEARER=1` and a strong bearer token.
- **Receipt retention**: define a retention policy for `instance/trace.db`.
- **Secure storage**: ensure trace DB and logs are on encrypted disks if required.
- **Network policy**: disable external tools or enforce outbound restrictions.

## Honest Boundaries

- Orchestrators-v2 does **not** provide certified compliance.
- This is a framework with safety-first defaults and auditable receipts.
- You own the operational controls, retention, and access policies.
