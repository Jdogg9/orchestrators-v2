# Semantic Router Operator’s Guide

This guide helps you tune the semantic router’s thresholds using the trace data it emits.

## Prerequisites

- Enable semantic routing: `ORCH_SEMANTIC_ROUTER_ENABLED=1`
- Enable trace storage: `ORCH_TRACE_ENABLED=1`
- Ensure your trace DB path is set (default: `instance/trace.db`)

## What Gets Traced

When semantic routing runs, the server records a `semantic_router` step with:

- `candidates`: top matches with scores
- `decision`: the final route decision (tool, confidence, reason)

## Quick SQL Queries (SQLite)

> Run with: `sqlite3 instance/trace.db "..."`

### 1) See recent semantic router candidates

```sql
SELECT trace_id, created_at, step_json
FROM trace_steps
WHERE step_type = 'semantic_router'
ORDER BY created_at DESC
LIMIT 20;
```

### 2) Extract decision + top scores (JSON1 enabled)

```sql
SELECT
  trace_id,
  json_extract(step_json, '$.decision.tool') AS decision_tool,
  json_extract(step_json, '$.decision.confidence') AS decision_confidence,
  json_extract(step_json, '$.candidates[0].tool') AS top_tool,
  json_extract(step_json, '$.candidates[0].score') AS top_score,
  json_extract(step_json, '$.candidates[1].tool') AS runner_tool,
  json_extract(step_json, '$.candidates[1].score') AS runner_score
FROM trace_steps
WHERE step_type = 'semantic_router'
ORDER BY created_at DESC
LIMIT 50;
```

### 3) Spot ambiguous matches (small score gaps)

```sql
SELECT
  trace_id,
  json_extract(step_json, '$.candidates[0].score') AS top_score,
  json_extract(step_json, '$.candidates[1].score') AS runner_score,
  (json_extract(step_json, '$.candidates[0].score') - json_extract(step_json, '$.candidates[1].score')) AS score_gap
FROM trace_steps
WHERE step_type = 'semantic_router'
  AND json_extract(step_json, '$.candidates[1].score') IS NOT NULL
ORDER BY score_gap ASC
LIMIT 25;
```

## Tuning Strategy

1. **Start conservative**
   - Keep `ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY` high (default: `0.80`).
   - Watch for `no_match` decisions in traces when the router declines.

2. **Inspect top candidates**
   - If the wrong tool is often close to the right one, keep the threshold high and add deterministic rules instead.
   - If the top score is good but the router declines, lower the similarity threshold slightly.

3. **Watch score gaps**
   - The ambiguity guard rejects matches where the gap is small.
   - If you see frequent near-ties, consider improving tool descriptions or adding explicit rules.

4. **Update safely**
   - Adjust `ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY` in `.env`.
   - Re-test with the targeted command:

```bash
pytest -q tests/test_semantic_router.py tests/test_sandbox.py tests/test_tool_policy_conditions.py
```

## Operational Defaults

- Semantic routing is **disabled by default** for deterministic guarantees.
- Policy enforcement still applies to semantic matches (`ORCH_TOOL_POLICY_ENFORCE=1`).
- Unsafe tools remain sandboxed when `ORCH_TOOL_SANDBOX_REQUIRED=1`.
