# Intent Router (Multi-Tier Front Door)

The Intent Router is the canonical entry point for routing in ORCHESTRATORS_V2. It wraps the existing deterministic Rule + Semantic routing stack and adds confidence gating, cache short-circuiting, and HITL escalation.

## Goals

- **Single front door**: All routing decisions flow through one pipeline.
- **Policy-bound tiers**: Confidence thresholds and HITL triggers are policy-backed.
- **Auditability**: Every decision is traced with policy hash and evidence.
- **Determinism**: Rule and semantic routing remain deterministic, but now tiered.

## Tier Pipeline

| Tier | Purpose | Source | Outcome |
| --- | --- | --- | --- |
| Tier 0 | Hard rule gate | Rule or Policy Router | Immediate allow/deny based on rules and deny patterns. |
| Tier 1 | Cache short-circuit | Intent Cache | Returns stable decision when policy hash and signature match. |
| Tier 2 | Semantic routing | Semantic Router | Selects tool via embeddings, applying confidence + gap thresholds. |
| Tier 3 | HITL escalation | HITL Queue | Enqueues ambiguous/high-risk intent for review. |

## Shadow Mode

Shadow mode allows the intent router to **observe and trace** without changing runtime behavior.

- Enable shadow mode to capture intent decisions while still using the legacy router.
- Disabling shadow mode makes the intent router authoritative.

## Configuration

### Core Flags

- `ORCH_INTENT_ROUTER_ENABLED` (default: 0)
- `ORCH_INTENT_ROUTER_SHADOW` (default: 0)

### Cache Flags

- `ORCH_INTENT_CACHE_ENABLED` (default: 1)
- `ORCH_INTENT_CACHE_DB_PATH` (default: instance/intent_cache.db)
- `ORCH_INTENT_CACHE_TTL_SEC` (default: 600)

### HITL Flags

- `ORCH_INTENT_HITL_ENABLED` (default: 1)
- `ORCH_INTENT_HITL_DB_PATH` (default: instance/hitl_queue.db)

### Semantic Thresholds

- `ORCH_INTENT_MIN_CONFIDENCE` (default: 0.85)
- `ORCH_INTENT_MIN_GAP` (default: 0.05)

## Policy Schema

`config/tool_policy.yaml` supports intent routing metadata:

```yaml
policy:
  intent_router:
    ambiguity:
      min_confidence: 0.85
      min_gap: 0.05
      action: hitl
    hitl:
      message: "Ambiguous intent detected. Human review required."
```

Optional per-intent overrides can be declared under `intents`:

```yaml
intents:
  - id: web_search
    min_confidence_tier2: 0.90
    min_gap_tier2: 0.10
    tier3_required: true
```

## Trace Output

Intent router decisions are written to the trace steps table as `intent_router` events. Each event includes:

- `decision_id`
- `policy_hash`
- `tier_used`
- `intent_id`
- `confidence`, `gap`
- `requires_hitl`
- `deny_reason`
- `evidence` (top-k semantic scores, guard messages, HITL request ID)

## HITL Queue

When intent is ambiguous or requires escalation, the router enqueues a HITL request with:

- decision metadata
- top-k semantic scores
- guard reason and message

Queue entries are stored in SQLite (`hitl_queue` table).