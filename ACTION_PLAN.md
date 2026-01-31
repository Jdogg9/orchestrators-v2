# ORCHESTRATORS_V2 — Prioritized Action Plan

## P0 — Required for Production (Blocking)

- Tool sandboxing (subprocess/container isolation) ✅
  - Why it matters: Prevents arbitrary code/tool execution from impacting the host.
  - Rough effort: L

- Auth enabled by default in non-dev ✅
  - Why it matters: Eliminates unauthenticated access to protected endpoints in real environments.
  - Rough effort: S

- Replace SQLite with Postgres (or KV) ✅ (Postgres default in production; SQLite WAL fallback)
  - Why it matters: Enables concurrency, durability, and operational scaling.
  - Rough effort: M

- Provider circuit breakers + timeouts
  - Why it matters: Protects system availability when LLM backends degrade or fail.
  - Rough effort: S

- Metrics wired to dashboard + alerts ✅
  - Why it matters: Enables SLOs, rapid incident detection, and capacity planning.
  - Rough effort: M

## P1 — Strongly Recommended

- Redis-backed rate limiting ✅ (required in production)
- Structured tracing export (OpenTelemetry)
- Tool execution quotas
- SAST in CI
- Signed commits + branch protection

## P2 — Strategic Enhancements

- Planning router
- Cost-aware routing
- Multi-agent coordination
- Policy engine for tools
- Admin UI

## Ownership Model (Optional)

- Core: routing + memory
- Ops: deployment + observability
- Security: sandbox + auth
