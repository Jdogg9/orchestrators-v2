from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from src.advanced_router import ModelRouter, PolicyRouter
from src.intent_router import IntentRouter
from src.llm_provider import get_provider
from src.router import Rule, RuleRouter, RouteDecision
from src.orchestrator_memory import apply_semantic_ambiguity_guard
from src.semantic_router import SemanticRouter, SemanticMatch
from src.tracer import (
    get_tracer,
    record_pruning_event,
    record_summary_generation_latency,
    record_tier_transition,
    record_token_utilization_ratio,
)
from src.tool_registry import ToolRegistry, ToolSpec
from src.tools.math import evaluate_expression, SafeMathError
from src.tools.orch_tokenizer import orch_tokenizer


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
        messages, budget_info = self._apply_token_budget(messages, trace_id=trace_id)
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
            self._record_token_usage(trace_id, messages, hitl_message, budget_info)
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
            self._record_token_usage(
                trace_id,
                messages,
                self._tool_response_content(decision, tool_result),
                budget_info,
            )
            return {
                "assistant_content": self._tool_response_content(decision, tool_result),
                "route_decision": decision,
                "intent_decision": intent_decision,
                "tool_result": tool_result,
                "model_decision": None,
                "semantic_candidates": semantic_candidates[:2],
            }

        if os.getenv("ORCH_LLM_ENABLED", "0") == "1":
            model_decision = self.model_router.select_model(
                messages,
                tool_selected=False,
                token_count=budget_info.get("input_tokens"),
            )
            record_tier_transition(self._tier_for_model_decision(model_decision))
            provider = get_provider(model_override=model_decision.model)
            llm_response = provider.generate(messages)
            self._record_token_usage(trace_id, messages, llm_response.content, budget_info)
            return {
                "assistant_content": llm_response.content,
                "route_decision": decision,
                "intent_decision": intent_decision,
                "tool_result": None,
                "model_decision": model_decision,
                "semantic_candidates": semantic_candidates[:2],
            }

        stub_content = f"[ORCHESTRATORS_V2 stub] You said: {user_input}"
        self._record_token_usage(trace_id, messages, stub_content, budget_info)
        return {
            "assistant_content": stub_content,
            "route_decision": decision,
            "intent_decision": intent_decision,
            "tool_result": None,
            "model_decision": None,
            "semantic_candidates": semantic_candidates[:2],
        }

    @staticmethod
    def _tier_for_model_decision(model_decision) -> str:
        if not model_decision:
            return "unknown"
        reason = str(model_decision.reason or "").lower()
        if reason == "tier3_summary_required":
            return "tier3"
        if reason in {"tier1_overflow", "tier2_overflow", "analysis_request"}:
            return "tier2"
        if reason == "default_chat":
            return "tier1"
        return "tier1"

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

        self.registry.register(
            ToolSpec(
                name="orch_tokenizer",
                description="Encode/decode/count tokens using the local GPT-AIMEE tokenizer",
                handler=orch_tokenizer,
                safe=True,
                requires_sandbox=False,
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

    def _record_token_usage(
        self,
        trace_id: Optional[str],
        messages: List[Dict[str, str]],
        assistant_content: str,
        budget_info: Dict[str, Any],
    ) -> None:
        if not trace_id:
            return
        tracer = get_tracer()
        input_tokens = budget_info.get("input_tokens")
        output_tokens = self._count_tokens_for_text(assistant_content)
        budget_tokens = budget_info.get("budget_tokens")
        utilization = None
        utilization_ratio = None
        if budget_tokens and input_tokens is not None:
            utilization = round((input_tokens / budget_tokens) * 100, 2)
            utilization_ratio = input_tokens / budget_tokens
        record_token_utilization_ratio(utilization_ratio)
        tracer.record_step(
            trace_id,
            "token_usage",
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "context_utilization_percentage": utilization,
                "token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "context_utilization_percentage": utilization,
                },
                "budget_tokens": budget_tokens,
            },
        )

    def _apply_token_budget(
        self,
        messages: List[Dict[str, str]],
        trace_id: Optional[str] = None,
    ) -> tuple[List[Dict[str, str]], Dict[str, Any]]:
        budget_tokens = int(os.getenv("ORCH_MAX_TOKENS", "16384"))
        tier3_min_tokens = int(os.getenv("ORCH_TIER3_MIN_TOKENS", "32768"))
        force_summary = False
        info: Dict[str, Any] = {
            "budget_tokens": budget_tokens,
            "input_tokens": None,
            "pruned_turns": 0,
            "summary_added": False,
        }
        if budget_tokens <= 0:
            info["input_tokens"] = self._count_tokens_for_messages(messages)
            return messages, info

        total_tokens = self._count_tokens_for_messages(messages)
        info["input_tokens"] = total_tokens
        if total_tokens <= budget_tokens:
            return messages, info
        if total_tokens > tier3_min_tokens:
            force_summary = True

        system_indices = {idx for idx, msg in enumerate(messages) if msg.get("role") == "system"}
        first_user_idx = next((idx for idx, msg in enumerate(messages) if msg.get("role") == "user"), None)

        pinned_indices = set(system_indices)
        if first_user_idx is not None:
            pinned_indices.add(first_user_idx)
            if first_user_idx + 1 < len(messages):
                if messages[first_user_idx + 1].get("role") == "assistant":
                    pinned_indices.add(first_user_idx + 1)

        for idx, msg in enumerate(messages):
            metadata = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
            if msg.get("pinned") or metadata.get("pinned") or metadata.get("priority") == "pinned":
                pinned_indices.add(idx)
            if metadata.get("goal") is True:
                pinned_indices.add(idx)

        turns = self._build_turns(messages)
        protected_turns = {0, len(turns) - 1} if turns else set()

        removable_turns = []
        for turn_index, turn_indices in enumerate(turns):
            if turn_index in protected_turns:
                continue
            if any(idx in pinned_indices for idx in turn_indices):
                continue
            priority = self._turn_priority(turn_indices, messages)
            removable_turns.append((priority, turn_indices))

        removable_turns.sort(key=lambda item: item[0])

        removed_indices: List[int] = []
        for _, turn_indices in removable_turns:
            if total_tokens <= budget_tokens:
                break
            for idx in turn_indices:
                removed_indices.append(idx)
            pruned_messages = [msg for i, msg in enumerate(messages) if i not in set(removed_indices)]
            total_tokens = self._count_tokens_for_messages(pruned_messages)
            info["pruned_turns"] += 1

        removed_messages: List[Dict[str, str]] = []
        if removed_indices:
            removed_set = set(removed_indices)
            removed_messages = [msg for i, msg in enumerate(messages) if i in removed_set]
            messages = [msg for i, msg in enumerate(messages) if i not in removed_set]

        summary_enabled = force_summary or os.getenv("ORCH_TOKEN_BUDGET_SUMMARY_ENABLED", "0") == "1"
        if removed_messages and summary_enabled:
            summary_text = self._summarize_removed(removed_messages)
            if summary_text:
                insert_at = max(system_indices) + 1 if system_indices else 0
                if first_user_idx is not None:
                    insert_at = min(insert_at, first_user_idx + 1)
                summary_message = {
                    "role": "system",
                    "content": summary_text,
                    "metadata": {"pinned": True, "summary": "pruned_context"},
                }
                messages = messages[:insert_at] + [summary_message] + messages[insert_at:]
                info["summary_added"] = True

        info["input_tokens"] = self._count_tokens_for_messages(messages)
        if trace_id and info["pruned_turns"]:
            tracer = get_tracer()
            tracer.record_step(
                trace_id,
                "token_budget_prune",
                {
                    "budget_tokens": budget_tokens,
                    "input_tokens": info["input_tokens"],
                    "pruned_turns": info["pruned_turns"],
                    "summary_added": info["summary_added"],
                    "summary_forced": force_summary,
                },
            )
            record_pruning_event(info["summary_added"], force_summary)

        return messages, info

    def _build_turns(self, messages: List[Dict[str, str]]) -> List[List[int]]:
        turns: List[List[int]] = []
        current: List[int] = []
        for idx, msg in enumerate(messages):
            role = msg.get("role")
            if role == "system":
                continue
            if role == "user":
                if current:
                    turns.append(current)
                current = [idx]
            else:
                if current:
                    current.append(idx)
                else:
                    current = [idx]
        if current:
            turns.append(current)
        return turns

    def _turn_priority(self, indices: List[int], messages: List[Dict[str, str]]) -> float:
        priorities = []
        for idx in indices:
            msg = messages[idx]
            metadata = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
            priority_value = metadata.get("priority")
            if isinstance(priority_value, (int, float)):
                priorities.append(float(priority_value))
                continue
            if priority_value in {"high", "pinned"}:
                priorities.append(100.0)
                continue
            if priority_value == "medium":
                priorities.append(50.0)
                continue
            if priority_value == "low":
                priorities.append(10.0)
                continue
            recency = (idx + 1) / max(len(messages), 1)
            priorities.append(20.0 + recency * 30.0)
        return min(priorities) if priorities else 0.0

    def _summarize_removed(self, removed_messages: List[Dict[str, str]]) -> str:
        if not removed_messages:
            return ""
        removed_text = []
        for msg in removed_messages:
            content = str(msg.get("content", "")).strip()
            if content:
                removed_text.append(f"{msg.get('role', 'unknown')}: {content}")
        if not removed_text:
            return ""
        from src.tools.summarize import summarize_text

        start_time = time.time()
        summary_payload = summarize_text("\n".join(removed_text))
        record_summary_generation_latency(time.time() - start_time)
        summary = summary_payload.get("summary", "") if isinstance(summary_payload, dict) else ""
        if summary:
            return f"Previous Context Summary: {summary}"
        return ""

    def _count_tokens_for_messages(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            payload = orch_tokenizer(action="count", text=content)
            if payload.get("status") == "ok":
                total += int(payload.get("token_count", 0))
            else:
                total += max(1, len(content) // 4)
        return total

    def _count_tokens_for_text(self, text: str) -> int:
        if not text:
            return 0
        payload = orch_tokenizer(action="count", text=text)
        if payload.get("status") == "ok":
            return int(payload.get("token_count", 0))
        return max(1, len(text) // 4)

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
