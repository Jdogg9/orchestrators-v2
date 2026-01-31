# ORCHESTRATORS_V2 — Release Notes (V2.0)

**Release date:** 2026-01-30

## Highlights

- **Production-grade observability**
  - W3C Trace Context response headers (`traceparent`, `X-Trace-Id`) for end-to-end trace pickup.
  - OTel context helpers centralized in `src/observability.py`.
  - Trace receipts recorded in SQLite for per-request forensics.

- **Security & boundary hardening**
  - Public boundary sanitization (`scripts/sanitize_strings.sh`).
  - CI secret scanning via `scripts/secret_scan.sh`.
  - Deterministic tool policy enforcement.

- **Routing & tool safety**
  - Policy-driven routing with `config/router_policy.yaml`.
  - Sandboxed execution for unsafe tools (Docker).
  - AST-based safe calculator wired into `safe_calc` tool.

- **Operational readiness**
  - `/ready` gate with dependency health checks.
  - Prometheus `/metrics` endpoint and bundled observability stack configs.
  - JSON logs with request IDs and latency.

## Notable Changes

- **Trace context propagation**
  - Response headers now include W3C trace context to support client-side correlation.
  - Trace IDs can be lifted directly from network traces and matched in SQLite receipts.

- **Safe calculator tool**
  - Replaced eval-based calculator with AST-safe evaluator.
  - Deterministic error taxonomy for invalid expressions.

## Upgrade Notes

- If you rely on the `safe_calc` tool, no API changes are required. Behavior is now AST-safe.
- For distributed tracing, ensure your client respects the `traceparent` response header.

## Verification Checklist

```bash
./scripts/verify_public_boundary.sh
./scripts/secret_scan.sh
pytest -q
```

## Known Warnings

- Flask-Limiter in-memory store warning during tests (intentional for local runs). Use Redis in production via `ORCH_RATE_LIMIT_STORAGE_URL`.
