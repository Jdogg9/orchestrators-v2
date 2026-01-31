# Killer Demo: Local Receipts + Boundary Verification

This demo proves the philosophy in minutes: local execution, receipts, and boundary verification.

## 3-Command Quickstart

```bash
# 1) From repo root
cd ORCHESTRATORS_V2

# 2) Run the demo
python examples/killer_demo_local_receipts/run_demo.py

# 3) Optional: inspect receipts
cat $(python examples/killer_demo_local_receipts/run_demo.py --skip-boundary --skip-exfiltration | grep RECEIPT_PATH | cut -d= -f2)
```

## Expected Output (abridged)

```
RECEIPT_PATH=/tmp/orch_receipts_xxxx/demo_receipt.json
TRACE_DB_PATH=/tmp/orch_receipts_xxxx/trace.db
PASS: simulated exfiltration attempt blocked
PASS: boundary verified
PASS: demo complete
```

## Where Receipts Are Stored

- Receipt JSON: `/tmp/orch_receipts_*/demo_receipt.json`
- Trace DB: `/tmp/orch_receipts_*/trace.db`

> These are local, ephemeral receipts. Set `ORCH_TRACE_DB_PATH` if you want a persistent location.
