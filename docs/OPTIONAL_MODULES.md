# Optional Modules (Roadmap)

These modules are intentionally **optional** so the core remains deterministic,
local-first, and auditable.

## Planning & Scheduling

- Lightweight task planning layer
- Explicit scheduling interface (cron-style or queue-driven)
- Defaults off; no implicit autonomy

## Cost-aware Routing

- Budget caps per user/session
- Provider routing based on cost/latency/quality
- Requires explicit enable flag

## Multi-agent Coordination (Opt-in)

- Simple agent graph runner as a separate package
- Clear boundaries for memory + receipts
- Audit-friendly message envelopes

## Preflight Reviewer (Opt-in)

- Optional “preflight” advisory step before tool execution (see [PREFLIGHT_REVIEWER.md](PREFLIGHT_REVIEWER.md))
- Produces a structured risk summary (never exposed to end users)
- Must remain disabled unless it meets the same receipt + redaction requirements

## Status

These modules are not in core and should remain **opt-in** until they can meet
policy, sandbox, and receipt requirements.
