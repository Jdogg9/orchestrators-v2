from __future__ import annotations

import os
from pathlib import Path

import yaml

from src.intent_cache import IntentCache
from src.intent_router import IntentRouter
from src.hitl_queue import HitlQueue
from src.orchestrator_memory import apply_semantic_ambiguity_guard
from src.router import Rule, RuleRouter, RouteDecision
from src.semantic_router import SemanticMatch


class MappingSemanticRouter:
    def __init__(self, mapping):
        self.enabled = True
        self._mapping = mapping

    def route_with_diagnostics(self, user_input: str):
        payload = self._mapping.get(user_input, {})
        tool = payload.get("tool")
        score = payload.get("score", 0.0)
        decision = RouteDecision(tool=tool, params={}, confidence=score, reason="semantic_match")
        candidates = []
        if tool:
            candidates.append(SemanticMatch(tool=tool, score=score))
        runner_up = payload.get("runner_up")
        if runner_up:
            candidates.append(SemanticMatch(tool=runner_up.get("tool"), score=runner_up.get("score", 0.0)))
        return decision, candidates


def _load_cases() -> list[dict]:
    path = Path(__file__).with_name("golden_intents.yaml")
    payload = yaml.safe_load(path.read_text())
    return payload.get("cases", [])


def _build_policy(tmp_path: Path) -> Path:
    policy_path = tmp_path / "policy.yaml"
    policy = {
        "policy": {
            "intent_router": {
                "tier0": {
                    "deny_patterns": ["rm -rf", "drop database"],
                    "allow_patterns": ["status"],
                },
                "hitl": {"message": "HITL required"},
            }
        },
        "intents": [
            {"id": "python_exec", "tier3_required": True},
            {"id": "web_search", "tier3_required": True},
        ],
    }
    policy_path.write_text(yaml.safe_dump(policy))
    return policy_path


def _build_rule_router() -> RuleRouter:
    router = RuleRouter()
    router.add_rule(
        Rule(
            tool="echo",
            predicate=lambda text: text.strip().lower().startswith("echo "),
            param_builder=lambda text: {},
            confidence=0.9,
            reason="keyword_echo",
        )
    )
    router.add_rule(
        Rule(
            tool="safe_calc",
            predicate=lambda text: text.strip().lower().startswith("calc "),
            param_builder=lambda text: {},
            confidence=0.9,
            reason="keyword_calc",
        )
    )
    return router


def _legacy_route(user_input: str, rule_router: RuleRouter, semantic_router: MappingSemanticRouter, policy_payload: dict):
    decision = rule_router.route(user_input)
    candidates = []
    if not decision.tool:
        semantic_decision, candidates = semantic_router.route_with_diagnostics(user_input)
        if semantic_decision.tool:
            decision = semantic_decision
    guard = apply_semantic_ambiguity_guard(decision, candidates)
    intents = policy_payload.get("intents", []) or []
    tier3_required = any(intent.get("id") == decision.tool and intent.get("tier3_required") for intent in intents)
    if not guard.get("allowed", True) or tier3_required:
        return decision, candidates, True
    return decision, candidates, False


def test_golden_set_intent_router(tmp_path, monkeypatch):
    cases = _load_cases()
    policy_path = _build_policy(tmp_path)
    monkeypatch.setenv("ORCH_TOOL_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ORCH_INTENT_ROUTER_ENABLED", "1")
    monkeypatch.setenv("ORCH_INTENT_MIN_CONFIDENCE", "0.85")
    monkeypatch.setenv("ORCH_INTENT_MIN_GAP", "0.05")

    mapping = {}
    for case in cases:
        semantic = case.get("semantic")
        if semantic:
            mapping[case["prompt"]] = semantic

    semantic_router = MappingSemanticRouter(mapping)
    rule_router = _build_rule_router()
    cache = IntentCache(db_path=str(tmp_path / "intent_cache.db"))
    hitl_queue = HitlQueue(db_path=str(tmp_path / "hitl_queue.db"))
    router = IntentRouter(rule_router, semantic_router, cache, hitl_queue, str(policy_path), enabled=True)
    policy_payload = yaml.safe_load(policy_path.read_text()) or {}

    for case in cases:
        decision = router.route(case["prompt"])
        expected = case["expected"]
        assert decision.tier_used == expected["tier_used"], case["id"]
        assert decision.intent_id == expected["intent_id"], case["id"]
        assert decision.requires_hitl == expected["requires_hitl"], case["id"]
        assert decision.deny_reason == expected["deny_reason"], case["id"]


def test_shadow_mismatch_budget(tmp_path, monkeypatch, capsys):
    cases = _load_cases()
    policy_path = _build_policy(tmp_path)
    monkeypatch.setenv("ORCH_TOOL_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("ORCH_INTENT_ROUTER_ENABLED", "1")
    monkeypatch.setenv("ORCH_INTENT_MIN_CONFIDENCE", "0.85")
    monkeypatch.setenv("ORCH_INTENT_MIN_GAP", "0.05")

    mapping = {}
    for case in cases:
        semantic = case.get("semantic")
        if semantic:
            mapping[case["prompt"]] = semantic

    semantic_router = MappingSemanticRouter(mapping)
    rule_router = _build_rule_router()
    cache = IntentCache(db_path=str(tmp_path / "intent_cache.db"))
    hitl_queue = HitlQueue(db_path=str(tmp_path / "hitl_queue.db"))
    router = IntentRouter(rule_router, semantic_router, cache, hitl_queue, str(policy_path), enabled=True)
    policy_payload = yaml.safe_load(policy_path.read_text()) or {}

    total = 0
    mismatches = 0
    safe_mismatches = 0
    high_risk_mismatches = 0
    tier_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    hitl_count = 0
    max_safe_mismatches = int(os.getenv("ORCH_SHADOW_MAX_SAFE_MISMATCHES", "0"))
    for case in cases:
        if not case.get("shadow_compare", True):
            continue
        total += 1
        intent_decision = router.route(case["prompt"])
        legacy_decision, _candidates, legacy_hitl = _legacy_route(case["prompt"], rule_router, semantic_router, policy_payload)

        tier_counts[intent_decision.tier_used] = tier_counts.get(intent_decision.tier_used, 0) + 1
        if intent_decision.requires_hitl:
            hitl_count += 1

        expected_intent = case.get("expected", {}).get("intent_id")
        risk = case.get("risk") or ("high" if expected_intent in {"web_search", "python_exec"} else "safe")

        if intent_decision.intent_id != legacy_decision.tool:
            mismatches += 1
            if risk == "high":
                high_risk_mismatches += 1
            else:
                safe_mismatches += 1
            continue
        if bool(intent_decision.requires_hitl) != bool(legacy_hitl):
            mismatches += 1
            if risk == "high":
                high_risk_mismatches += 1
            else:
                safe_mismatches += 1

    ratio = (mismatches / total) if total else 0.0
    hitl_rate = (hitl_count / total) if total else 0.0
    print(f"Golden cases: {len(cases)}")
    print(
        "Shadow mismatch summary: "
        f"total={total} mismatches={mismatches} "
        f"safe_mismatches={safe_mismatches} high_risk_mismatches={high_risk_mismatches} "
        f"tier_counts={tier_counts} hitl_rate={hitl_rate:.2%}"
    )

    assert high_risk_mismatches == 0
    assert safe_mismatches <= max_safe_mismatches
