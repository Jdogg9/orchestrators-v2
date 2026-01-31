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

## Status

These modules are not in core and should remain **opt-in** until they can meet
policy, sandbox, and receipt requirements.
