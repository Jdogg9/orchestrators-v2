from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class RouteDecision:
    tool: Optional[str]
    params: Dict[str, str]
    confidence: float
    reason: str


@dataclass(frozen=True)
class Rule:
    tool: str
    predicate: Callable[[str], bool]
    param_builder: Callable[[str], Dict[str, str]]
    confidence: float = 0.7
    reason: str = "rule_match"


class RuleRouter:
    """Rule-based router (deterministic, explainable)."""

    def __init__(self) -> None:
        self._rules: List[Rule] = []

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def route(self, user_input: str) -> RouteDecision:
        for rule in self._rules:
            if rule.predicate(user_input):
                return RouteDecision(
                    tool=rule.tool,
                    params=rule.param_builder(user_input),
                    confidence=rule.confidence,
                    reason=rule.reason,
                )
        return RouteDecision(tool=None, params={}, confidence=0.0, reason="no_match")
