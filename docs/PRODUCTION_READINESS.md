# Production Readiness

This repo is a **reference implementation**. Below is a short, concrete checklist for production hardening.

## Gaps (Intentional)

- **Tool execution policy**: Only minimal registry exists. No policy engine, quotas, or sandbox.
- **Advanced routing**: Rule router only; no planning, cost tracking, or multi-agent coordination.
- **Storage scaling**: SQLite is default; no distributed tracing or replicated storage.
- **Ops surface**: No deployment manifests, SLO dashboards, or incident runbooks.
- **Security controls**: Boundary + tests only; no static analysis pipeline or secret scanning service.

## Recommended Hardening Steps

1. **Provider isolation**
   - Run LLM provider behind a dedicated gateway.
   - Implement timeouts, retries, and circuit breakers.

2. **Tool sandboxing**
   - Use subprocess isolation or containers for any code execution.
   - Enforce allowlists and scoped permissions.

3. **Storage upgrade**
   - Swap SQLite for Postgres or an internal KV store.
   - Add TTL enforcement at the database layer.

4. **Observability**
   - Emit structured traces to a centralized system.
   - Add request IDs, latency percentiles, and error budgets.

5. **Security automation**
   - Add SAST/DAST and secret scanning in CI.
   - Enforce branch protections and signed commits.

## Scope Disclaimer

This repo stays small by design. The goal is to show **how to reason about guardrails**, not to ship a full platform.
