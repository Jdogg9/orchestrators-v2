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

    def check(self, tool_name: str, safe: bool) -> PolicyDecision:
        if not self._enforce:
            return PolicyDecision(allowed=True, reason="policy_disabled")

        if not self._rules:
            return PolicyDecision(allowed=False, reason="policy_missing")

        for rule in self._rules:
            pattern = rule.get("match") or rule.get("tool")
            if not pattern:
                continue
            if not re.search(pattern, tool_name, flags=re.IGNORECASE):
                continue

            require_safe = rule.get("require_safe")
            if require_safe is True and not safe:
                return PolicyDecision(allowed=False, reason="policy_requires_safe", rule=pattern)

            action = rule.get("action", "allow").lower()
            reason = rule.get("reason", "policy_rule")
            if action == "deny":
                return PolicyDecision(allowed=False, reason=reason, rule=pattern)
            return PolicyDecision(allowed=True, reason=reason, rule=pattern)

        return PolicyDecision(allowed=False, reason="policy_default_deny")
