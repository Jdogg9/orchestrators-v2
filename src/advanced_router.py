from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml

from src.router import RouteDecision


@dataclass(frozen=True)
class ModelDecision:
    model: str
    reason: str


class PolicyRouter:
    """Policy-driven router loaded from YAML (deterministic + auditable)."""

    def __init__(self, rules: List[Dict[str, str]], defaults: Optional[Dict[str, object]] = None) -> None:
        self._rules = rules
        self._defaults = defaults or {}

    @classmethod
    def from_env(cls) -> "PolicyRouter":
        policy_path = os.getenv("ORCH_ROUTER_POLICY_PATH", "config/router_policy.yaml")
        with open(policy_path, "r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        rules = payload.get("rules", [])
        defaults = payload.get("defaults", {})
        return cls(rules=rules, defaults=defaults)

    def route(self, user_input: str) -> RouteDecision:
        for rule in self._rules:
            if rule.get("enabled", True) is False:
                continue

            patterns = []
            if rule.get("match"):
                patterns.append(rule.get("match"))
            if rule.get("match_any"):
                patterns.extend(rule.get("match_any") or [])
            if not patterns:
                continue

            case_insensitive = rule.get("case_insensitive", self._defaults.get("case_insensitive", True))
            flags = re.IGNORECASE if case_insensitive else 0
            if any(re.search(pattern, user_input, flags=flags) for pattern in patterns):
                params = dict(self._defaults.get("params", {}) or {})
                params.update(rule.get("params", {}) or {})
                return RouteDecision(
                    tool=rule.get("tool"),
                    params=params,
                    confidence=float(rule.get("confidence", self._defaults.get("confidence", 0.7))),
                    reason=rule.get("reason", rule.get("id", "policy_match")),
                )
        return RouteDecision(tool=None, params={}, confidence=0.0, reason="no_match")


class ModelRouter:
    """Model selector with cost-aware defaults and explainable reasons."""

    def __init__(self) -> None:
        self.model_chat = os.getenv("ORCH_MODEL_CHAT", "qwen2.5:3b")
        self.model_tool = os.getenv("ORCH_MODEL_TOOL", "qwen2.5:3b")
        self.model_reasoner = os.getenv("ORCH_MODEL_REASONER", self.model_chat)

    def select_model(self, user_input: str, tool_selected: bool) -> ModelDecision:
        if tool_selected:
            return ModelDecision(model=self.model_tool, reason="tool_selected")
        if len(user_input) > 1200:
            return ModelDecision(model=self.model_reasoner, reason="long_context")
        if any(keyword in user_input.lower() for keyword in ("analyze", "strategy", "threat model")):
            return ModelDecision(model=self.model_reasoner, reason="analysis_request")
        return ModelDecision(model=self.model_chat, reason="default_chat")
