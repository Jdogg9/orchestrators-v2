from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.advanced_router import ModelRouter, PolicyRouter
from src.llm_provider import get_provider
from src.router import Rule, RuleRouter, RouteDecision
from src.semantic_router import SemanticRouter
from src.tool_registry import ToolRegistry, ToolSpec
from src.tools.math import evaluate_expression, SafeMathError


class Orchestrator:
    """Production-oriented orchestrator with policy routing and sandboxing."""

    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self._register_default_tools()
        self.router = self._load_router()
        self.model_router = ModelRouter()
        self.semantic_router = SemanticRouter.from_env(self.registry.list_tools())

    def handle(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        user_input = self._last_user_message(messages)
        decision = self.router.route(user_input)
        semantic_candidates = []
        if not decision.tool and self.semantic_router.enabled:
            semantic_decision, semantic_candidates = self.semantic_router.route_with_diagnostics(user_input)
            if semantic_decision.tool:
                decision = semantic_decision

        if decision.tool:
            params = self._build_tool_params(decision, user_input)
            tool_result = self.registry.execute(decision.tool, **params)
            return {
                "assistant_content": self._tool_response_content(decision, tool_result),
                "route_decision": decision,
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
                "tool_result": None,
                "model_decision": model_decision,
                "semantic_candidates": semantic_candidates[:2],
            }

        return {
            "assistant_content": f"[ORCHESTRATORS_V2 stub] You said: {user_input}",
            "route_decision": decision,
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
                    requires_sandbox=False,
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
    def _last_user_message(messages: List[Dict[str, str]]) -> str:
        last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
        return last.get("content", "")
