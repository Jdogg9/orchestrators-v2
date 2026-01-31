# Operator Checklist (Daily/Release)

## Daily Ops

- [ ] Confirm API is enabled only when needed (`ORCH_ENABLE_API=1`).
- [ ] Verify boundary script passes: `./scripts/verify_public_boundary.sh`.
- [ ] Review recent receipts (trace DB) for anomalies.
- [ ] Ensure no `.env` files are tracked by git.

## Release Ops

- [ ] Run secret scan: `./scripts/secret_scan.sh`.
- [ ] Run tests: `pytest -q`.
- [ ] Verify docs are updated for new flags or examples.
- [ ] Confirm demo output still matches expected receipts.

## Incident Response

- [ ] Disable external tools (`ORCH_TOOL_WEB_SEARCH_ENABLED=0`).
- [ ] Set `ORCH_LLM_ENABLED=0` to force local-only stub mode.
- [ ] Capture trace DB for incident review.
