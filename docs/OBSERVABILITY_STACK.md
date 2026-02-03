# Observability Stack (OTel + Prometheus + Grafana)

This repo ships a preconfigured observability stack with:

- **OpenTelemetry Collector** for traces
- **Prometheus** for metrics scraping
- **Grafana** for dashboards
- **Alertmanager** for alerts

## One-command Full Stack

```bash
cp .env.production.example .env.production
# Rotate ORCH_BEARER_TOKEN before production use.

docker compose -f docker-compose.full.yml up --build
```

## Endpoints

- Orchestrator API: http://127.0.0.1:8088
- Prometheus: http://127.0.0.1:9090
- Alertmanager: http://127.0.0.1:9093
- Grafana: http://127.0.0.1:3000 (default admin/admin)

## What’s Wired

- `/metrics` exposes Prometheus counters + histograms.
- `deploy/observability/prometheus.yml` scrapes `orchestrators-v2:8088`.
- `deploy/observability/alerting_rules.yml` includes uptime + memory alerts.
- `deploy/observability/grafana-dashboard.json` plots request volume + latency.
- `deploy/observability/otel-collector.yaml` receives OTLP traces.

## Alerts

Alert rules live in:
- deploy/observability/alerting_rules.yml

Add email/webhook integrations in:
- deploy/observability/alertmanager.yml

## Notes

- Metrics require auth in production (Bearer token).
- The Collector currently logs traces; attach a backend (Tempo, Jaeger, or OTLP gateway) as needed.

## OTLP Integration

To export traces to an external collector, set:

```
ORCH_OTEL_ENABLED=1
ORCH_OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318/v1/traces
```

Compatible backends include:
- Grafana Tempo
- Jaeger (OTLP)
- OpenTelemetry Collector pipelines

## Retention & Scrubbing

- Keep trace DBs out of version control.
- Rotate logs based on operator retention policies.
- Trust Panel endpoints return **redacted** metadata only.

Related:
- [Trust Panel](TRUST_PANEL.md)
