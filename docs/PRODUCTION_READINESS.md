# Production Readiness

This repo is a **reference implementation**. Below is a short, concrete checklist for production hardening.

## Shipped Hardening (Now Included)

- **Deployment artifacts**: Dockerfile, docker-compose.yml, and a systemd unit template.
- **App server**: Gunicorn config for production process management.
- **Readiness endpoint**: `/ready` gate for dependency health.
- **Metrics endpoint**: `/metrics` for Prometheus scraping (toggleable).
- **Request controls**: Max request size and basic rate limiting.
- **Rate limiting backend**: Optional Redis storage via `ORCH_RATE_LIMIT_STORAGE_URL`.
- **Structured logs**: JSON logging with request IDs and latency.
- **Advanced routing (optional)**: Policy-driven router via `config/router_policy.yaml`.
- **Sandboxed tools (optional)**: Docker-based execution for unsafe tools.
- **Tool policy engine (optional)**: Deterministic allow/deny rules via `config/tool_policy.yaml`.
- **Storage upgrade (optional)**: Postgres support via `ORCH_DATABASE_URL`.
- **Tracing**: OpenTelemetry support with OTLP exporter.
- **Dashboards + alerting**: Prometheus/Grafana + Alertmanager config in `deploy/observability`.
- **Secret scan in CI**: `scripts/secret_scan.sh` runs on every push/PR.
- **Security automation**: Bandit + pip-audit (plus optional Semgrep/Trivy).
- **Optional dynamic scan**: OWASP ZAP baseline script (`scripts/dynamic_scan.sh`).
- **Optional signed-commit checks**: `scripts/verify_signed_commits.sh` (env-gated).

## Gaps (Intentional)

- **Tool policy depth**: No user-scoped policy engine or quotas for sandboxed tools.
- **Routing depth**: Policy router is deterministic but does not do cost or reinforcement learning.
- **Observability stack**: Alert routing and long-term storage require operator configuration.
- **Security controls**: DAST and signed-commit enforcement are optional, not default.

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
