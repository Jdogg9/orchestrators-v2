# Production Readiness

This repo is a **reference implementation**. Below is a short, concrete checklist for production hardening.

## Shipped Hardening (Now Included)

- **Deployment artifacts**: Dockerfile, docker-compose.yml, and a systemd unit template.
- **App server**: Gunicorn config for production process management.
- **Readiness endpoint**: `/ready` gate for dependency health.
- **Metrics endpoint**: `/metrics` for Prometheus scraping (toggleable).
- **Request controls**: Max request size and basic rate limiting.
   - **Note**: Rate limiting defaults to in-memory storage (best-effort). Configure a real backend (e.g., Redis) for production.
- **Structured logs**: JSON logging with request IDs and latency.
- **Secret scan in CI**: `scripts/secret_scan.sh` runs on every push/PR.

## Gaps (Intentional)

- **Tool execution policy**: Only minimal registry exists. No policy engine, quotas, or sandbox.
- **Advanced routing**: Rule router only; no planning, cost tracking, or multi-agent coordination.
- **Storage scaling**: SQLite is default; no distributed tracing or replicated storage.
- **Ops surface**: No SLO dashboards, incident runbooks, or live paging integration.
- **Security controls**: Boundary + tests only; no SAST/DAST integration beyond local secret scan.

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
   - Wire `/metrics` into a dashboard and alerting pipeline.

5. **Security automation**
   - Add SAST/DAST and secret scanning in CI.
   - Enforce branch protections and signed commits.

## Scope Disclaimer

This repo stays small by design. The goal is to show **how to reason about guardrails**, not to ship a full platform.
