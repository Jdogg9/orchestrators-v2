from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.advanced_router import ModelRouter, PolicyRouter
from src.intent_router import IntentRouter
from src.llm_provider import get_provider
from src.router import Rule, RuleRouter, RouteDecision
from src.orchestrator_memory import apply_semantic_ambiguity_guard
from src.semantic_router import SemanticRouter, SemanticMatch
from src.tracer import get_tracer
from src.tool_registry import ToolRegistry, ToolSpec
from src.tools.math import evaluate_expression, SafeMathError


class Orchestrator:
    """Production-oriented orchestrator with policy routing and sandboxing."""

    def __init__(
        self,
        shadow_total_counter=None,
        shadow_mismatch_counter=None,
    ) -> None:
        self.registry = ToolRegistry()
        self._register_default_tools()
        self.router = self._load_router()
        self.model_router = ModelRouter()
        self.semantic_router = SemanticRouter.from_env(self.registry.list_tools())
        self.intent_router = IntentRouter.from_env(self.router, self.semantic_router)
        self.shadow_total_counter = shadow_total_counter
        self.shadow_mismatch_counter = shadow_mismatch_counter

    def handle(self, messages: List[Dict[str, str]], trace_id: Optional[str] = None) -> Dict[str, Any]:
        user_input = self._last_user_message(messages)
        intent_decision = None
        intent_shadow = os.getenv("ORCH_INTENT_ROUTER_SHADOW", "0") == "1"
        semantic_candidates: List[SemanticMatch] = []
        hitl_message = None
        if self.intent_router.enabled:
            intent_decision = self.intent_router.route(user_input, trace_id=trace_id)
            semantic_candidates = self._semantic_candidates_from_intent(intent_decision)

            if not intent_shadow:
                if intent_decision.requires_hitl or intent_decision.deny_reason:
                    hitl_reason = intent_decision.deny_reason or "hitl_required"
                    hitl_decision = RouteDecision(
                        tool=None,
                        params={},
                        confidence=float(intent_decision.confidence or 0.0),
                        reason=hitl_reason,
                    )
                    return {
                        "assistant_content": intent_decision.evidence.get(
                            "hitl_message", "Human review required."
                        ),
                        "route_decision": hitl_decision,
                        "intent_decision": intent_decision,
                        "tool_result": None,
                        "model_decision": None,
                        "semantic_candidates": semantic_candidates[:2],
                    }

                if intent_decision.intent_id:
                    decision = RouteDecision(
                        tool=intent_decision.intent_id,
                        params=intent_decision.tool_params or {},
                        confidence=float(intent_decision.confidence or 0.0),
                        reason="intent_router",
                    )
                else:
                    decision = RouteDecision(
                        tool=None,
                        params={},
                        confidence=float(intent_decision.confidence or 0.0),
                        reason="intent_router_no_match",
                    )
            else:
                decision, semantic_candidates, hitl_message = self._legacy_route(user_input, trace_id)
                self._record_shadow_metrics(intent_decision, decision, bool(hitl_message))
        else:
            decision, semantic_candidates, hitl_message = self._legacy_route(user_input, trace_id)

        if hitl_message:
            return {
                "assistant_content": hitl_message,
                "route_decision": decision,
                "intent_decision": intent_decision,
                "tool_result": None,
                "model_decision": None,
                "semantic_candidates": semantic_candidates[:2],
            }

        if decision.tool:
            params = self._build_tool_params(decision, user_input)
            tool_result = self.registry.execute(decision.tool, trace_id=trace_id, **params)
            return {
                "assistant_content": self._tool_response_content(decision, tool_result),
                "route_decision": decision,
                "intent_decision": intent_decision,
                "tool_result": tool_result,
                "model_decision": None,
                "semantic_candidates": semantic_candidates[:2],
            }

        if os.getenv("ORCH_LLM_ENABLED", "0") == "1":
            model_decision = self.model_router.select_model(user_input, tool_selected=False)
            provider = get_provider(model_override=model_decision.model)
            llm_response = provider.generate(messages)
            return {
                "assistant_content": llm_response.content,
                "route_decision": decision,
                "intent_decision": intent_decision,
                "tool_result": None,
                "model_decision": model_decision,
                "semantic_candidates": semantic_candidates[:2],
            }

        return {
            "assistant_content": f"[ORCHESTRATORS_V2 stub] You said: {user_input}",
            "route_decision": decision,
            "intent_decision": intent_decision,
            "tool_result": None,
            "model_decision": None,
            "semantic_candidates": semantic_candidates[:2],
        }

    def _load_router(self):
        policy_path = os.getenv("ORCH_ROUTER_POLICY_PATH", "config/router_policy.yaml")
        if os.path.exists(policy_path):
            return PolicyRouter.from_env()

        router = RuleRouter()
        router.add_rule(
            Rule(
                tool="safe_calc",
                predicate=lambda text: "calc" in text.lower(),
                param_builder=lambda text: {"expression": text.lower().replace("calc", "").strip()},
                confidence=0.8,
                reason="keyword_calc",
            )
        )
        router.add_rule(
            Rule(
                tool="echo",
                predicate=lambda text: "echo" in text.lower(),
                param_builder=lambda text: {"message": text.lower().replace("echo", "").strip()},
                confidence=0.6,
                reason="keyword_echo",
            )
        )
        return router

    def _register_default_tools(self) -> None:
        self.registry.register(
            ToolSpec(
                name="echo",
                description="Echo user input",
                handler=lambda message: f"Echo: {message}",
                safe=True,
            )
        )
        self.registry.register(
            ToolSpec(
                name="safe_calc",
                description="Safely evaluate arithmetic expressions",
                handler=self._safe_calc,
                safe=True,
            )
        )
        self.registry.register(
            ToolSpec(
                name="python_eval",
                description="Evaluate Python expressions inside a locked-down sandbox",
                handler=lambda **_: "sandbox_required",
                safe=False,
                sandbox_command=["python", "/tools/python_eval.py"],
                requires_sandbox=True,
            )
        )
        self.registry.register(
            ToolSpec(
                name="python_exec",
                description="Execute multi-line Python scripts inside a locked-down sandbox",
                handler=lambda **_: "sandbox_required",
                safe=False,
                sandbox_command=["python", "/tools/python_exec.py"],
                requires_sandbox=True,
            )
        )

        if os.getenv("ORCH_TOOL_WEB_SEARCH_ENABLED", "0") == "1":
            from src.tools.web_search import web_search

            self.registry.register(
                ToolSpec(
                    name="web_search",
                    description="Search the public web (DuckDuckGo) for non-sensitive queries",
                    handler=web_search,
                    safe=False,
                    requires_sandbox=True,
                    sandbox_command=["python", "/tools/web_search.py"],
                )
            )

        from src.tools.summarize import summarize_text
        self.registry.register(
            ToolSpec(
                name="summarize_text",
                description="Summarize text locally without an LLM",
                handler=summarize_text,
                safe=True,
                requires_sandbox=False,
            )
        )

    def _safe_calc(self, expression: str) -> float:
        try:
            return evaluate_expression(expression)
        except SafeMathError as exc:
            raise ValueError(str(exc)) from exc

    def _build_tool_params(self, decision: RouteDecision, user_input: str) -> Dict[str, Any]:
        params = decision.params or {}
        if "expression_key" in params:
            return {params["expression_key"]: self._strip_prefix(user_input, "calc")}
        if "message_key" in params:
            return {params["message_key"]: self._strip_prefix(user_input, "echo")}
        if decision.tool == "safe_calc":
            return {"expression": self._strip_prefix(user_input, "calc")}
        if decision.tool == "python_eval":
            return {"expression": user_input}
        if decision.tool == "python_exec":
            return {"code": user_input}
        if decision.tool == "echo":
            return {"message": self._strip_prefix(user_input, "echo")}
        return {"input": user_input}

    def _strip_prefix(self, text: str, keyword: str) -> str:
        lowered = text.lower()
        return lowered.replace(keyword, "", 1).strip()

    def _tool_response_content(self, decision: RouteDecision, tool_result: Dict[str, Any]) -> str:
        if tool_result.get("status") != "ok":
            return f"Tool error ({decision.tool}): {tool_result.get('error')}"
        return f"Tool [{decision.tool}] result: {tool_result.get('result')}"

    @staticmethod
    def _semantic_candidates_from_intent(intent_decision) -> List[SemanticMatch]:
        if not intent_decision:
            return []
        topk = intent_decision.evidence.get("semantic_topk") or []
        return [SemanticMatch(tool=item["tool"], score=item["score"]) for item in topk if "tool" in item]

    def _record_shadow_metrics(self, intent_decision, legacy_decision: RouteDecision, legacy_hitl: bool) -> None:
        if not self.shadow_total_counter or not self.shadow_mismatch_counter:
            return
        self.shadow_total_counter.inc()

        if not intent_decision:
            return

        intent_tool = intent_decision.intent_id
        if intent_tool != legacy_decision.tool:
            self.shadow_mismatch_counter.inc()
            return

        if bool(intent_decision.requires_hitl) != bool(legacy_hitl):
            self.shadow_mismatch_counter.inc()

    def _legacy_route(self, user_input: str, trace_id: Optional[str]) -> tuple[RouteDecision, List[SemanticMatch], Optional[str]]:
        decision = self.router.route(user_input)
        semantic_candidates: List[SemanticMatch] = []
        if not decision.tool and self.semantic_router.enabled:
            semantic_decision, semantic_candidates = self.semantic_router.route_with_diagnostics(user_input)
            if semantic_decision.tool:
                decision = semantic_decision

        guard = apply_semantic_ambiguity_guard(decision, semantic_candidates)
        if trace_id:
            tracer = get_tracer()
            tracer.record_step(trace_id, "semantic_ambiguity_guard", guard)
        if not guard.get("allowed", True):
            hitl_decision = RouteDecision(
                tool=None,
                params={},
                confidence=guard.get("confidence", 0.0) or 0.0,
                reason=guard.get("reason", "hitl_required"),
            )
            return hitl_decision, semantic_candidates, guard.get("message", "Human review required.")

        return decision, semantic_candidates, None

    @staticmethod
    def _last_user_message(messages: List[Dict[str, str]]) -> str:
        last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
        return last.get("content", "")
