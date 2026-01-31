from __future__ import annotations

import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml

from src.memory import PII_PATTERNS, SECRET_PATTERNS
from src.intent_cache import IntentCache
from src.hitl_queue import HitlQueue
from src.policy_engine import compute_policy_hash
from src.router import RouteDecision
from src.semantic_router import SemanticRouter, SemanticMatch
from src.orchestrator_memory import apply_semantic_ambiguity_guard
from src.tracer import get_tracer


CONTROL_CHARS_PATTERN = r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+"


@dataclass(frozen=True)
class IntentDecision:
    decision_id: str
    policy_hash: Optional[str]
    tier_used: int
    intent_id: Optional[str]
    allowed_tools: List[str]
    tool_params: Dict[str, Any]
    requires_hitl: bool
    confidence: float
    gap: Optional[float]
    deny_reason: Optional[str]
    evidence: Dict[str, Any]
    operator: Optional[Dict[str, Any]]
    cacheable: bool


class IntentRouter:
    def __init__(
        self,
        base_router,
        semantic_router: SemanticRouter,
        cache: IntentCache,
        hitl_queue: HitlQueue,
        policy_path: str,
        enabled: bool,
    ) -> None:
        self.base_router = base_router
        self.semantic_router = semantic_router
        self.cache = cache
        self.hitl_queue = hitl_queue
        self.policy_path = policy_path
        self.enabled = enabled

    @classmethod
    def from_env(cls, base_router, semantic_router: SemanticRouter) -> "IntentRouter":
        policy_path = os.getenv("ORCH_TOOL_POLICY_PATH", "config/tool_policy.yaml")
        enabled = os.getenv("ORCH_INTENT_ROUTER_ENABLED", "0") == "1"
        cache_enabled = os.getenv("ORCH_INTENT_CACHE_ENABLED", "1") == "1"
        cache = IntentCache(enabled=cache_enabled)
        hitl_queue = HitlQueue()
        return cls(base_router, semantic_router, cache, hitl_queue, policy_path, enabled)

    def route(self, user_input: str, trace_id: Optional[str] = None) -> IntentDecision:
        if not self.enabled:
            return self._decision(
                tier=0,
                intent_id=None,
                confidence=0.0,
                deny_reason="intent_router_disabled",
                evidence={"note": "intent_router_disabled"},
                cacheable=False,
                requires_hitl=False,
            )

        policy_payload, policy_hash = self._load_policy()
        normalized = self._normalize_input(user_input)
        signature = self._signature(normalized)

        tier0 = self._tier0_rule(policy_payload, policy_hash, user_input)
        if tier0:
            self._record_trace(trace_id, tier0)
            return tier0

        tier1 = self._tier1_cache(policy_hash, signature)
        if tier1:
            self._record_trace(trace_id, tier1)
            return tier1

        tier2 = self._tier2_semantic(policy_payload, policy_hash, user_input)
        tier2 = self._maybe_enqueue_hitl(policy_payload, tier2)
        self._record_trace(trace_id, tier2)

        if tier2.cacheable and not tier2.requires_hitl:
            self.cache.set(policy_hash or "", signature, tier2.__dict__, stable=True)

        return tier2

    def _tier0_rule(self, policy_payload: Dict[str, Any], policy_hash: Optional[str], user_input: str) -> Optional[IntentDecision]:
        tier0_cfg = (((policy_payload.get("policy") or {}).get("intent_router") or {}).get("tier0") or {})
        deny_patterns = tier0_cfg.get("deny_patterns", []) or []
        allow_patterns = tier0_cfg.get("allow_patterns", []) or []
        hitl_message = (((policy_payload.get("policy") or {}).get("intent_router") or {}).get("hitl") or {}).get(
            "message",
            "Ambiguous intent detected. Human review required.",
        )

        for pattern in deny_patterns:
            if re.search(pattern, user_input, flags=re.IGNORECASE):
                return self._decision(
                    tier=0,
                    intent_id=None,
                    confidence=1.0,
                    deny_reason="tier0_deny",
                    evidence={"rules_matched": [pattern]},
                    cacheable=False,
                    requires_hitl=False,
                    policy_hash=policy_hash,
                )

        decision = self.base_router.route(user_input)
        if decision.tool:
            intent_cfg = self._intent_config(policy_payload, decision.tool)
            requires_hitl = bool(intent_cfg.get("tier3_required", False)) if intent_cfg else False
            return self._decision(
                tier=0,
                intent_id=decision.tool,
                confidence=decision.confidence,
                deny_reason="tier3_required" if requires_hitl else None,
                evidence={"rules_matched": [decision.reason], "hitl_message": hitl_message},
                cacheable=False,
                requires_hitl=requires_hitl,
                policy_hash=policy_hash,
                allowed_tools=[decision.tool],
                tool_params=decision.params,
            )

        for pattern in allow_patterns:
            if re.search(pattern, user_input, flags=re.IGNORECASE):
                return self._decision(
                    tier=0,
                    intent_id="allow_pattern",
                    confidence=0.9,
                    deny_reason=None,
                    evidence={"rules_matched": [pattern]},
                    cacheable=False,
                    requires_hitl=False,
                    policy_hash=policy_hash,
                    allowed_tools=[],
                )

        return None

    def _tier1_cache(self, policy_hash: Optional[str], signature: str) -> Optional[IntentDecision]:
        if not policy_hash:
            return None
        cached = self.cache.get(policy_hash, signature)
        if not cached:
            return None
        payload = dict(cached.decision_json)
        payload["tier_used"] = 1
        payload["evidence"] = {**(payload.get("evidence") or {}), "cache_hit": True}
        return IntentDecision(**payload)

    def _tier2_semantic(self, policy_payload: Dict[str, Any], policy_hash: Optional[str], user_input: str) -> IntentDecision:
        semantic_decision, candidates = self.semantic_router.route_with_diagnostics(user_input)
        guard = apply_semantic_ambiguity_guard(semantic_decision, candidates)
        guard_triggered = not guard.get("allowed", True)

        gap = None
        if len(candidates) > 1:
            gap = float(candidates[0].score - candidates[1].score)

        intent_id = semantic_decision.tool
        intent_cfg = self._intent_config(policy_payload, intent_id) if intent_id else None
        tier3_required = bool(intent_cfg.get("tier3_required", False)) if intent_cfg else False

        requires_hitl = guard_triggered or tier3_required
        deny_reason = guard.get("reason") if guard_triggered else None

        min_confidence = float(intent_cfg.get("min_confidence_tier2", os.getenv("ORCH_INTENT_MIN_CONFIDENCE", "0.85"))) if intent_cfg else float(os.getenv("ORCH_INTENT_MIN_CONFIDENCE", "0.85"))
        min_gap = float(intent_cfg.get("min_gap_tier2", os.getenv("ORCH_INTENT_MIN_GAP", "0.05"))) if intent_cfg else float(os.getenv("ORCH_INTENT_MIN_GAP", "0.05"))

        cacheable = bool(
            intent_id
            and not requires_hitl
            and (semantic_decision.confidence >= min_confidence)
            and (gap is None or gap >= min_gap)
        )

        evidence = {
            "semantic_topk": [
                {"tool": cand.tool, "score": cand.score} for cand in candidates[:3]
            ],
            "guard_triggered": guard_triggered,
            "guard_message": guard.get("message"),
        }
        if guard_triggered:
            evidence["hitl_message"] = guard.get("message") or "Human review required."

        return self._decision(
            tier=2,
            intent_id=intent_id,
            confidence=semantic_decision.confidence,
            gap=gap,
            deny_reason=deny_reason,
            evidence=evidence,
            cacheable=cacheable,
            requires_hitl=requires_hitl,
            policy_hash=policy_hash,
            allowed_tools=[intent_id] if intent_id else [],
            tool_params={},
        )

    def _maybe_enqueue_hitl(self, policy_payload: Dict[str, Any], decision: IntentDecision) -> IntentDecision:
        if not decision.requires_hitl:
            return decision

        hitl_cfg = (((policy_payload.get("policy") or {}).get("intent_router") or {}).get("hitl") or {})
        payload = {
            "decision_id": decision.decision_id,
            "intent_id": decision.intent_id,
            "confidence": decision.confidence,
            "gap": decision.gap,
            "evidence": decision.evidence,
        }
        hitl_request = self.hitl_queue.enqueue(payload)
        evidence = dict(decision.evidence)
        if hitl_request:
            evidence["hitl_request_id"] = hitl_request.request_id
        message = hitl_cfg.get("message") or "Ambiguous intent detected. Human review required."
        evidence["hitl_message"] = message
        return IntentDecision(
            **{
                **decision.__dict__,
                "deny_reason": decision.deny_reason or "hitl_required",
                "evidence": evidence,
                "cacheable": False,
                "operator": None,
            }
        )

    def _load_policy(self) -> tuple[Dict[str, Any], Optional[str]]:
        if not os.path.exists(self.policy_path):
            return {}, None
        with open(self.policy_path, "rb") as handle:
            raw = handle.read()
        payload = yaml.safe_load(raw) or {}
        policy_hash = compute_policy_hash(raw, os.getenv("ORCH_TOOL_POLICY_ENFORCE", "0") == "1")
        return payload, policy_hash

    @staticmethod
    def _intent_config(policy_payload: Dict[str, Any], intent_id: Optional[str]) -> Dict[str, Any]:
        if not intent_id:
            return {}
        intents = policy_payload.get("intents", []) or []
        for intent in intents:
            if intent.get("id") == intent_id:
                return intent
        return {}

    @staticmethod
    def _normalize_input(text: str) -> str:
        normalized = re.sub(CONTROL_CHARS_PATTERN, " ", text or "")
        normalized = IntentRouter._scrub_for_signature(normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip().lower()

    @staticmethod
    def _scrub_for_signature(text: str) -> str:
        scrubbed = text
        for pattern in SECRET_PATTERNS:
            scrubbed = re.sub(pattern, "[REDACTED]", scrubbed, flags=re.IGNORECASE)
        for pattern in PII_PATTERNS:
            scrubbed = re.sub(pattern, "[REDACTED]", scrubbed, flags=re.IGNORECASE)
        return scrubbed

    @staticmethod
    def _signature(text: str) -> str:
        digest = hashlib.sha256(text.encode()).hexdigest()
        return digest[:32]

    def _decision(
        self,
        *,
        tier: int,
        intent_id: Optional[str],
        confidence: float,
        deny_reason: Optional[str],
        evidence: Dict[str, Any],
        cacheable: bool,
        requires_hitl: bool,
        policy_hash: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        tool_params: Optional[Dict[str, Any]] = None,
        gap: Optional[float] = None,
        operator: Optional[Dict[str, Any]] = None,
    ) -> IntentDecision:
        return IntentDecision(
            decision_id=str(uuid.uuid4()),
            policy_hash=policy_hash,
            tier_used=tier,
            intent_id=intent_id,
            allowed_tools=allowed_tools or [],
            tool_params=tool_params or {},
            requires_hitl=requires_hitl,
            confidence=confidence,
            gap=gap,
            deny_reason=deny_reason,
            evidence=evidence,
            operator=operator,
            cacheable=cacheable,
        )

    @staticmethod
    def _record_trace(trace_id: Optional[str], decision: IntentDecision) -> None:
        if not trace_id:
            return
        tracer = get_tracer()
        tracer.record_step(
            trace_id,
            "intent_router",
            {
                "decision_id": decision.decision_id,
                "policy_hash": decision.policy_hash,
                "tier_used": decision.tier_used,
                "intent_id": decision.intent_id,
                "allowed_tools": decision.allowed_tools,
                "tool_params": decision.tool_params,
                "requires_hitl": decision.requires_hitl,
                "confidence": decision.confidence,
                "gap": decision.gap,
                "deny_reason": decision.deny_reason,
                "evidence": decision.evidence,
                "cacheable": decision.cacheable,
            },
        )