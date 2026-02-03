# Quickstart Walkthrough

This walkthrough demonstrates the minimal operator flow: start the server, run stub chat, enable LLM safely, approve a tool, and verify via the Trust Panel.

## 1) Start the server (stub mode)

```bash
cp .env.example .env
python -m src.server
```

Ensure LLM remains disabled:
```
ORCH_LLM_ENABLED=0
```

Send a stub chat request:
```bash
curl -X POST http://127.0.0.1:8088/v1/chat/completions \
  -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

## 2) Enable LLM safely

Follow the checklist:
- [LLM Enablement Checklist](LLM_ENABLEMENT_CHECKLIST.md)
- [LLM Provider Contract](LLM_PROVIDER_CONTRACT.md)

Then set:
```
ORCH_LLM_ENABLED=1
ORCH_LLM_NETWORK_ENABLED=1
```

## 3) Approve a tool execution

Request approval:
```bash
curl -X POST http://127.0.0.1:8088/v1/tools/approve \
  -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"python_exec","args":{"code":"print(1)"}}'
```

Execute with approval token:
```bash
curl -X POST http://127.0.0.1:8088/v1/tools/execute \
  -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"python_exec","args":{"code":"print(1)"},"approval_token":"<approval_id>"}'
```

## 4) Verify execution receipts (Trust Panel)

Enable Trust Panel:
```
ORCH_TRUST_PANEL_ENABLED=1
```

Fetch recent events:
```bash
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  "http://127.0.0.1:8088/v1/trust/events?limit=10"
```

Fetch a specific trace:
```bash
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  "http://127.0.0.1:8088/v1/trust/trace/<trace_id>"
```

Verify chain hash:
```bash
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  "http://127.0.0.1:8088/v1/trust/verify/<trace_id>?expected_hash=<hash>"
```

## Related Docs

- [Trust Panel](TRUST_PANEL.md)
- [Tool Approval Contract](TOOL_APPROVAL_CONTRACT.md)
- [Operator Contract](OPERATOR_CONTRACT.md)
- [Production Readiness](PRODUCTION_READINESS.md)
