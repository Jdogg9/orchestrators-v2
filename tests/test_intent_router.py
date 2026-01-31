import os
from pathlib import Path

import yaml

from src.intent_cache import IntentCache
from src.intent_router import IntentRouter
from src.hitl_queue import HitlQueue
from src.policy_engine import compute_policy_hash
from src.router import Rule, RuleRouter, RouteDecision
from src.semantic_router import SemanticMatch


class StubSemanticRouter:
    def __init__(self, decision: RouteDecision, candidates):
        self.enabled = True
        self._decision = decision
        self._candidates = candidates

    def route_with_diagnostics(self, _user_input):
        return self._decision, self._candidates


def _write_policy(tmp_path: Path, payload: dict) -> Path:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(payload))
    return policy_path


def test_intent_router_tier0_rule_match(tmp_path, monkeypatch):
    policy_path = _write_policy(tmp_path, {"policy": {"intent_router": {"hitl": {"message": "Review"}}}})
    monkeypatch.setenv("ORCH_TOOL_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ORCH_INTENT_ROUTER_ENABLED", "1")

    rule_router = RuleRouter()
    rule_router.add_rule(
        Rule(
            tool="echo",
            predicate=lambda text: "echo" in text.lower(),
            param_builder=lambda text: {},
            confidence=0.9,
            reason="keyword_echo",
        )
    )

    semantic_router = StubSemanticRouter(RouteDecision(tool=None, params={}, confidence=0.0, reason="no_match"), [])
    cache = IntentCache(db_path=str(tmp_path / "intent_cache.db"))
    hitl_queue = HitlQueue(db_path=str(tmp_path / "hitl_queue.db"))
    router = IntentRouter(rule_router, semantic_router, cache, hitl_queue, str(policy_path), enabled=True)

    decision = router.route("echo hello")
    assert decision.tier_used == 0
    assert decision.intent_id == "echo"
    assert decision.requires_hitl is False


def test_intent_router_tier1_cache_hit(tmp_path, monkeypatch):
    policy_path = _write_policy(tmp_path, {"policy": {}})
    monkeypatch.setenv("ORCH_TOOL_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ORCH_INTENT_ROUTER_ENABLED", "1")
    monkeypatch.setenv("ORCH_TOOL_POLICY_ENFORCE", "0")

    policy_bytes = policy_path.read_bytes()
    policy_hash = compute_policy_hash(policy_bytes, False)

    cache = IntentCache(db_path=str(tmp_path / "intent_cache.db"), enabled=True)
    signature = "abc123"
    cached_decision = {
        "decision_id": "cache-1",
        "policy_hash": policy_hash,
        "tier_used": 2,
        "intent_id": "echo",
        "allowed_tools": ["echo"],
        "tool_params": {},
        "requires_hitl": False,
        "confidence": 0.99,
        "gap": 0.2,
        "deny_reason": None,
        "evidence": {"cached": True},
        "operator": None,
        "cacheable": True,
    }
    cache.set(policy_hash, signature, cached_decision, stable=True)

    router = IntentRouter(
        RuleRouter(),
        StubSemanticRouter(RouteDecision(tool=None, params={}, confidence=0.0, reason="no_match"), []),
        cache,
        HitlQueue(db_path=str(tmp_path / "hitl_queue.db")),
        str(policy_path),
        enabled=True,
    )

    decision = router._tier1_cache(policy_hash, signature)
    assert decision is not None
    assert decision.tier_used == 1
    assert decision.evidence.get("cache_hit") is True


def test_intent_router_tier2_hitl_queue(tmp_path, monkeypatch):
    policy_path = _write_policy(
        tmp_path,
        {"policy": {"intent_router": {"hitl": {"message": "HITL required"}}}},
    )
    monkeypatch.setenv("ORCH_TOOL_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ORCH_INTENT_ROUTER_ENABLED", "1")
    monkeypatch.setenv("ORCH_INTENT_MIN_CONFIDENCE", "0.9")
    monkeypatch.setenv("ORCH_INTENT_HITL_ENABLED", "1")

    semantic_decision = RouteDecision(tool="echo", params={}, confidence=0.5, reason="semantic_match")
    candidates = [SemanticMatch(tool="echo", score=0.5), SemanticMatch(tool="safe_calc", score=0.49)]

    router = IntentRouter(
        RuleRouter(),
        StubSemanticRouter(semantic_decision, candidates),
        IntentCache(db_path=str(tmp_path / "intent_cache.db")),
        HitlQueue(db_path=str(tmp_path / "hitl_queue.db")),
        str(policy_path),
        enabled=True,
    )

    decision = router.route("do something")
    assert decision.requires_hitl is True
    assert decision.deny_reason in {"hitl_low_confidence", "hitl_ambiguous", "hitl_required"}
    assert decision.evidence.get("hitl_message") == "HITL required"
