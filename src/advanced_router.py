from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml

from src.router import RouteDecision
from src.tools.orch_tokenizer import orch_tokenizer


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
        self.chat_tier1_max_tokens = int(os.getenv("ORCH_MODEL_CHAT_TIER1_MAX_TOKENS", "4096"))
        self.reasoner_tier1_max_tokens = int(
            os.getenv("ORCH_MODEL_REASONER_TIER1_MAX_TOKENS", "32768")
        )
        self.tier3_min_tokens = int(os.getenv("ORCH_TIER3_MIN_TOKENS", "32768"))
        self.tokenizer_model = os.getenv("ORCH_TOKENIZER_MODEL", "gpt-aimee")

    def select_model(
        self,
        messages: List[Dict[str, str]],
        tool_selected: bool,
        token_count: Optional[int] = None,
    ) -> ModelDecision:
        if tool_selected:
            return ModelDecision(model=self.model_tool, reason="tool_selected")

        total_tokens = token_count if token_count is not None else self._count_tokens(messages)

        if total_tokens > self.tier3_min_tokens:
            return ModelDecision(model=self.model_reasoner, reason="tier3_summary_required")
        if total_tokens > self.reasoner_tier1_max_tokens:
            return ModelDecision(model=self.model_reasoner, reason="tier2_overflow")
        if total_tokens > self.chat_tier1_max_tokens:
            return ModelDecision(model=self.model_reasoner, reason="tier1_overflow")
        if any(
            keyword in self._last_user_text(messages).lower()
            for keyword in ("analyze", "strategy", "threat model")
        ):
            return ModelDecision(model=self.model_reasoner, reason="analysis_request")
        return ModelDecision(model=self.model_chat, reason="default_chat")

    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            payload = orch_tokenizer(action="count", text=content, model_name=self.tokenizer_model)
            if payload.get("status") == "ok":
                total += int(payload.get("token_count", 0))
            else:
                total += max(1, len(content) // 4)
        return total

    @staticmethod
    def _last_user_text(messages: List[Dict[str, str]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return str(msg.get("content", ""))
        return ""
