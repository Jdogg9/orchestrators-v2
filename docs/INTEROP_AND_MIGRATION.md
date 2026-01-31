# Interop & Migration (Experimental)

This document provides a lightweight conceptual mapping from LangGraph/CrewAI constructs to Orchestrators-v2 primitives, plus a minimal translation example.

## Conceptual Mapping

| Concept | LangGraph / CrewAI | Orchestrators-v2 Equivalent |
| --- | --- | --- |
| Graph node / agent | Node / Agent | Tool + Router rule + optional agent profile |
| Edge / transition | Edge / Task flow | Rule + predicate + param builder |
| Shared state | Shared memory / context | Receipts + explicit tool inputs; optional memory (flagged) |
| Tooling | Tool registry / skill | ToolSpec + ToolRegistry |
| Traces / logs | Callbacks / logs | Trace receipts (DB + logs) |
| Governance | Human-in-the-loop | Policy engine + optional review hooks |

## Minimal Translation Example

### Input (Trivial Graph)

```json
{
  "nodes": [
    {"id": "echo", "type": "tool"},
    {"id": "safe_calc", "type": "tool"}
  ],
  "edges": [
    {"from": "echo", "to": "safe_calc", "when": "contains:calc"}
  ]
}
```

### Orchestrators-v2 Style

```python
from src.router import Rule, RuleRouter

router = RuleRouter()
router.add_rule(
    Rule(
        tool="safe_calc",
        predicate=lambda text: "calc" in text.lower(),
        param_builder=lambda text: {"expression": text.lower().replace("calc", "").strip()},
        confidence=0.8,
        reason="keyword_calc",
    )
)
```

## Experimental Converter

A tiny converter is provided for a trivial JSON-like graph format:

- [orchestrators_v2/interop/langgraph.py](../orchestrators_v2/interop/langgraph.py)

It is intentionally minimal and **not** a full LangGraph converter.
