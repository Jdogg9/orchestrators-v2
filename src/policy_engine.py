from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger("orchestrators_v2.policy")


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    rule: Optional[str] = None


class PolicyEngine:
    """Simple tool policy engine (deny/allow by regex).

    Rules are evaluated in order and should be deterministic/auditable.
    """

    def __init__(self, rules: List[Dict[str, str]], enforce: bool) -> None:
        self._rules = rules
        self._enforce = enforce

    @classmethod
    def from_env(cls) -> "PolicyEngine":
        enforce = os.getenv("ORCH_TOOL_POLICY_ENFORCE", "0") == "1"
        policy_path = os.getenv("ORCH_TOOL_POLICY_PATH", "config/tool_policy.yaml")
        if not os.path.exists(policy_path):
            logger.warning("Tool policy file missing", extra={"extra": {"path": policy_path}})
            return cls(rules=[], enforce=enforce)
        with open(policy_path, "r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        rules = payload.get("rules", [])
        return cls(rules=rules, enforce=enforce)

    def check(self, tool_name: str, safe: bool, params: Optional[Dict[str, object]] = None) -> PolicyDecision:
        if not self._enforce:
            return PolicyDecision(allowed=True, reason="policy_disabled")

        if not self._rules:
            return PolicyDecision(allowed=False, reason="policy_missing")

        params = params or {}
        for rule in self._rules:
            pattern = rule.get("match") or rule.get("tool")
            if not pattern:
                continue
            if not re.search(pattern, tool_name, flags=re.IGNORECASE):
                continue

            if not self._conditions_match(rule, params):
                return PolicyDecision(
                    allowed=False,
                    reason="deny:policy_condition_failed",
                    rule=pattern,
                )

            require_safe = rule.get("require_safe")
            if require_safe is True and not safe:
                return PolicyDecision(allowed=False, reason="policy_requires_safe", rule=pattern)

            action = rule.get("action", "allow").lower()
            reason = rule.get("reason", "policy_rule")
            if action == "deny":
                return PolicyDecision(allowed=False, reason=reason, rule=pattern)
            return PolicyDecision(allowed=True, reason=reason, rule=pattern)

        return PolicyDecision(allowed=False, reason="policy_default_deny")

    @staticmethod
    def _conditions_match(rule: Dict[str, object], params: Dict[str, object]) -> bool:
        conditions = rule.get("conditions")
        if not conditions:
            return True

        input_param = conditions.get("input_param", "input")
        if "max_input_len" in conditions or "min_input_len" in conditions:
            if input_param not in params:
                return False
            input_value = params.get(input_param)
            input_len = len(str(input_value)) if input_value is not None else 0
            max_len = conditions.get("max_input_len")
            min_len = conditions.get("min_input_len")
            if max_len is not None and input_len > int(max_len):
                return False
            if min_len is not None and input_len < int(min_len):
                return False

        return True
