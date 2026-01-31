from __future__ import annotations

from pathlib import Path

import yaml

from src.intent_cache import IntentCache
from src.intent_router import IntentRouter
from src.hitl_queue import HitlQueue
from src.router import RuleRouter, RouteDecision
from src.semantic_router import SemanticMatch


class StubSemanticRouter:
    def __init__(self, decision: RouteDecision, candidates: list[SemanticMatch]):
        self.enabled = True
        self._decision = decision
        self._candidates = candidates

    def route_with_diagnostics(self, _user_input: str):
        return self._decision, self._candidates


def _write_policy(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(payload))
    return path


def test_policy_hash_invalidates_cache(tmp_path):
    cache = IntentCache(db_path=str(tmp_path / "intent_cache.db"), enabled=True)
    cache.set(
        "hash-one",
        "signature-1",
        {
            "decision_id": "cache-1",
            "policy_hash": "hash-one",
            "tier_used": 2,
            "intent_id": "echo",
            "allowed_tools": ["echo"],
            "tool_params": {},
            "requires_hitl": False,
            "confidence": 0.95,
            "gap": 0.2,
            "deny_reason": None,
            "evidence": {"cached": True},
            "operator": None,
            "cacheable": True,
        },
        stable=True,
    )

    assert cache.get("hash-one", "signature-1") is not None
    assert cache.get("hash-two", "signature-1") is None


def test_hitl_decisions_not_cached(tmp_path, monkeypatch):
    policy_path = _write_policy(
        tmp_path,
        {
            "policy": {"intent_router": {"hitl": {"message": "Review"}}},
            "intents": [{"id": "web_search", "tier3_required": True}],
        },
    )
    monkeypatch.setenv("ORCH_TOOL_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ORCH_INTENT_ROUTER_ENABLED", "1")

    cache = IntentCache(db_path=str(tmp_path / "intent_cache.db"), enabled=True)
    signature = IntentRouter._signature(IntentRouter._normalize_input("Find the latest news"))

    router = IntentRouter(
        RuleRouter(),
        StubSemanticRouter(
            RouteDecision(tool="web_search", params={}, confidence=0.96, reason="semantic"),
            [SemanticMatch(tool="web_search", score=0.96)],
        ),
        cache,
        HitlQueue(db_path=str(tmp_path / "hitl_queue.db")),
        str(policy_path),
        enabled=True,
    )

    decision = router.route("Find the latest news")
    assert decision.requires_hitl is True
    assert cache.get(decision.policy_hash or "", signature) is None


def test_signature_scrubs_pii_and_secrets():
    sig_email_1 = IntentRouter._signature(
           IntentRouter._normalize_input("Contact me at test@local.test")
    )
    sig_email_2 = IntentRouter._signature(
           IntentRouter._normalize_input("Contact me at other@local.test")
    )
    sig_token = IntentRouter._signature(
        IntentRouter._normalize_input("Use token sk-proj-abcdef1234567890")
    )
    sig_token_alt = IntentRouter._signature(
        IntentRouter._normalize_input("Use token sk-proj-zzzzzz9876543210")
    )

    assert sig_email_1 == sig_email_2
    assert sig_token == sig_token_alt
