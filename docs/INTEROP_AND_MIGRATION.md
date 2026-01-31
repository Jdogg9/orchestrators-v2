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

## Experimental Converters

A tiny converter is provided for a trivial JSON-like graph format and a minimal
LangGraph/CrewAI subset:

- LangGraph subset: [orchestrators_v2/interop/langgraph.py](../orchestrators_v2/interop/langgraph.py)
- CrewAI subset: [orchestrators_v2/interop/crewai.py](../orchestrators_v2/interop/crewai.py)

It is intentionally minimal and **not** a full LangGraph/CrewAI converter.

## Migration Kit (Straightforward Path)

1. Export a minimal graph/task spec (subset) into JSON.
2. Convert to rules with the experimental converters.
3. Replace your router policy with the generated rules.
4. Run the local receipt + boundary demo to validate parity.

Example:

```python
from orchestrators_v2.interop.langgraph import convert_langgraph_spec, to_rule_router_snippet

rules = convert_langgraph_spec({
  "edges": [{"from": "router", "to": "safe_calc", "when": "contains:calc"}]
})
print(to_rule_router_snippet(rules))
```

### Supported Subset (LangGraph)

```json
{
  "edges": [
    {"from": "router", "to": "echo", "when": "contains:echo"},
    {"from": "router", "to": "safe_calc", "condition": "contains:calc"}
  ],
  "conditional_edges": [
    {"from": "router", "conditions": [
      {"when": "contains:news", "to": "web_search"}
    ]}
  ]
}
```

### Supported Subset (CrewAI)

```json
{
  "tasks": [
    {"tool": "web_search", "when": "contains:news"},
    {"tool": "safe_calc", "when": "contains:calc"}
  ]
}
```
