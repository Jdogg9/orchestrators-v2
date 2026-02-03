# Trust Panel (Receipts & Tamper-Evident Trace)

The Trust Panel exposes **redacted trace receipts** so operators can audit what happened without leaking prompts, tool args, or secrets.

## Status

- **Default**: Disabled
- **Enable**: Set `ORCH_TRUST_PANEL_ENABLED=1`
- **Debug metadata**: Optional (`ORCH_TRUST_PANEL_DEBUG=1`)

## What It Returns

- Redacted trace step metadata (`trace_steps`)
- Per-step event hashes
- A tamper-evident **chain hash** for the trace
- No raw prompts or tool arguments

Redaction rules:
- Known secret keys (Bearer tokens, API keys, JWTs) are replaced with `<redacted>`
- Email addresses are replaced with `<redacted>`
- Keys like `authorization`, `api_key`, `token`, `secret`, `password` are redacted
- Long values are truncated (default 500 chars)

## Endpoints

### 1) List recent trust events

`GET /v1/trust/events`

Query params:
- `limit` (int, optional)
- `step_type` (csv, optional) e.g., `tool_approval,llm_provider`
- `trace_id` (string, optional)
- `debug=1` (optional, requires `ORCH_TRUST_PANEL_DEBUG=1`)

Example:
```bash
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  "http://127.0.0.1:8088/v1/trust/events?limit=20&step_type=tool_approval"
```

### 2) Trace detail + chain hash

`GET /v1/trust/trace/<trace_id>`

Returns:
- `metadata` (redacted)
- `steps` (redacted, ordered)
- `chain_hash` (tamper-evident chain)

Example:
```bash
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  "http://127.0.0.1:8088/v1/trust/trace/$TRACE_ID"
```

### 3) Verify chain hash

`GET /v1/trust/verify/<trace_id>`

Optional:
- `expected_hash` (string)

Example:
```bash
curl -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  "http://127.0.0.1:8088/v1/trust/verify/$TRACE_ID?expected_hash=$HASH"
```

## How the Chain Works

Each trace step is hashed as:

$$
H_i = \text{SHA256}(\text{step\_type} \| \text{created\_at} \| \text{sanitized\_payload})
$$

The chain is:

$$
C_0 = 0^{64},\quad C_i = \text{SHA256}(C_{i-1} \| H_i)
$$

If any step changes, the final `chain_hash` changes.

## Dashboard Integration Ideas

- Grafana table showing `step_type`, `created_at`, and `event_hash`
- Alert if chain hash changes for the same trace id
- Link to `/v1/trust/trace/<trace_id>` from incident reports

## Related Docs

- [Observability Stack](OBSERVABILITY_STACK.md)
- [Operator Contract](OPERATOR_CONTRACT.md)
- [Tool Approval Contract](TOOL_APPROVAL_CONTRACT.md)
