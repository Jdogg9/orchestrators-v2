"""Experimental converter for a trivial JSON-like graph format.

This is NOT a full LangGraph adapter. It exists to provide a tiny bridge
for migration demos and documentation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuleSpec:
    tool: str
    match: str


def convert_graph(graph: Dict[str, object]) -> List[RuleSpec]:
    """Convert a tiny graph format to rule specs.

    Expected input:
    {
      "nodes": [{"id": "echo"}, {"id": "safe_calc"}],
      "edges": [{"from": "echo", "to": "safe_calc", "when": "contains:calc"}]
    }
    """
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    rules: List[RuleSpec] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        target = edge.get("to")
        condition = edge.get("when")
        if not target or not condition:
            continue
        rules.append(RuleSpec(tool=str(target), match=str(condition)))
    return rules


def to_rule_router_snippet(rules: List[RuleSpec]) -> str:
    """Render a minimal RuleRouter snippet for docs and demos."""
    lines = ["from src.router import Rule, RuleRouter", "", "router = RuleRouter()"]
    for rule in rules:
        if rule.match.startswith("contains:"):
            keyword = rule.match.split(":", 1)[1]
            lines.append(
                "router.add_rule(Rule(tool=\"%s\", predicate=lambda text: \"%s\" in text.lower(),"
                " param_builder=lambda text: {\"input\": text}, confidence=0.7, reason=\"interop\"))"
                % (rule.tool, keyword)
            )
        else:
            lines.append(
                "router.add_rule(Rule(tool=\"%s\", predicate=lambda text: True,"
                " param_builder=lambda text: {\"input\": text}, confidence=0.5, reason=\"interop\"))"
                % rule.tool
            )
    return "\n".join(lines)
