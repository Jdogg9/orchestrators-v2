# Production Deployment (High-Stakes Profile)

This guide deploys ORCHESTRATORS_V2 with **sandboxing**, **Postgres**, **Redis-backed rate limiting**, and **full observability**.

## Stack Components

- **Orchestrators API**: Gunicorn + Flask
- **Postgres**: Trace + memory candidate storage
- **Redis**: Rate limiting backend
- **OpenTelemetry Collector**: Trace forwarding
- **Prometheus**: Metrics scrape
- **Grafana**: Dashboards
- **Alertmanager**: Alert routing

## Files

- `deploy/docker-compose.prod.yml`
- `deploy/observability/otel-collector.yaml`
- `deploy/observability/prometheus.yml`
- `deploy/observability/alerting_rules.yml`
- `deploy/observability/alertmanager.yml`
- `deploy/observability/grafana-datasources.yml`
- `deploy/observability/grafana-dashboard.json`

## Environment (example)

```dotenv
ORCH_ORCHESTRATOR_MODE=advanced
ORCH_LLM_ENABLED=1
ORCH_REQUIRE_BEARER=1
ORCH_BEARER_TOKEN=change-me
ORCH_DATABASE_URL=postgresql+psycopg://orch:orch@postgres:5432/orch
ORCH_RATE_LIMIT_STORAGE_URL=redis://redis:6379/0
ORCH_TOOL_SANDBOX_ENABLED=1
ORCH_TOOL_SANDBOX_REQUIRED=1
ORCH_SANDBOX_TOOL_DIR=/app/sandbox_tools
ORCH_TOOL_POLICY_ENFORCE=1
ORCH_TOOL_POLICY_PATH=/app/config/tool_policy.yaml
ORCH_OTEL_ENABLED=1
ORCH_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
```

## Run (Docker Compose)

```bash
docker compose -f deploy/docker-compose.prod.yml up -d
```

## Verify

```bash
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" http://127.0.0.1:8088/ready
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" http://127.0.0.1:8088/metrics
```

## Notes

- Sandbox tools are executed in Docker with **network disabled** and **read-only** filesystem.
- Postgres is optional, but required for multi-node or audited deployments.
- Grafana ships a starter dashboard; customize for your SLOs.
