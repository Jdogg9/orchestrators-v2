# Deployment Recipes (Operator-Ready)

## Systemd (Local Host)

Use the existing unit template:

- [deploy/systemd/orchestrators-v2.service](../deploy/systemd/orchestrators-v2.service)

Suggested steps:

1. Copy to `/etc/systemd/system/`
2. Set environment variables in a dedicated file
3. `sudo systemctl daemon-reload`
4. `sudo systemctl enable --now orchestrators-v2.service`

## Docker (Local-Only)

Use the default compose file:

- [docker-compose.yml](../docker-compose.yml)

Suggested steps:

1. `cp .env.example .env`
2. `docker compose up --build`
3. Verify health: `curl http://127.0.0.1:8088/health`

## Hardening Notes

- Keep `ORCH_LLM_ENABLED=0` when operating fully offline.
- Disable external tools unless required.
- Store receipts on encrypted disks if needed.
