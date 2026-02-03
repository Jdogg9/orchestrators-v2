# Tool Approval Contract (ORCHESTRATORS_V2)

## Purpose

Provide a strict, auditable approval gate for unsafe tool execution with time-bound, consume-once semantics.

## Defaults (Safe-by-Default)

- **Approvals enforced** by default for unsafe tools: $\texttt{ORCH\_TOOL\_APPROVAL\_ENFORCE}=1$.
- **TTL**: $\texttt{ORCH\_TOOL\_APPROVAL\_TTL\_SEC}=900$ (15 minutes) unless overridden.
- **Consume-once**: approval tokens are invalid after first successful use.

## Endpoints

### 1) Issue Approval

**POST** /v1/tools/approve

**Request JSON**
- `name` (string, required): tool name
- `args` (object, optional): tool arguments
- `ttl_seconds` (int, optional): approval TTL override

**Response JSON**
- `approval_id`: approval token
- `tool`: tool name
- `args_hash`: SHA256 of normalized args
- `created_at`, `expires_at`
- `status`: "pending"

### 2) Execute Tool

**POST** /v1/tools/execute

**Request JSON**
- `name` (string, required): tool name
- `args` (object, optional): tool arguments
- `approval_token` (string, optional): required for unsafe tools when approvals enforced

**Response JSON**
- `result`: tool execution payload

## Validation Rules

An approval is valid only if **all** conditions hold:

1. Approval exists and is **pending**.
2. `tool` matches.
3. `args_hash` matches the request args.
4. Approval has **not expired**.
5. Approval has **not been consumed**.

If any rule fails, execution returns:

```json
{
  "status": "error",
  "tool": "<tool>",
  "error": "approval_required",
  "approval_reason": "<reason>"
}
```

Common `approval_reason` values:
- `missing_approval`
- `unknown_approval`
- `already_consumed`
- `tool_mismatch`
- `args_hash_mismatch`
- `expired`

## Storage

Approvals are stored in SQLite by default:
- Table: `tool_approvals`
- DB path: $\texttt{ORCH\_TOOL\_APPROVAL\_DB\_PATH}$ (default `instance/tool_approvals.db`)

## Threat Model Notes

- **TOCTOU**: consume-once semantics block token reuse.
- **Replay**: `args_hash` binding prevents mismatched execution.
- **Expiry**: TTL limits long-lived approvals.

## Minimal Example

1) Issue approval
```bash
curl -X POST http://127.0.0.1:8088/v1/tools/approve \
  -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"python_exec","args":{"code":"print(1)"}}'
```

2) Execute tool
```bash
curl -X POST http://127.0.0.1:8088/v1/tools/execute \
  -H "Authorization: Bearer $ORCH_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"python_exec","args":{"code":"print(1)"},"approval_token":"<approval_id>"}'
```
