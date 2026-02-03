from __future__ import annotations

import hashlib
import os
from typing import Tuple, Any, Dict, List

from flask import Blueprint, Response, current_app, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.agents import get_agent, inject_agent_prompt, list_agents
from src.llm_provider import get_provider
from src.orchestrator_memory import evaluate_memory_capture
from src.demo_mode import build_demo_response
from src.tracer import get_tracer
from src.policy_engine import load_policy_snapshot
from src.approval_store import ToolApprovalStore
from src.trust_panel import (
    trust_panel_enabled,
    list_trust_events,
    get_trace_report,
    verify_trace_chain,
)


def register_routes(app) -> Blueprint:
    limiter = app.config.get("ORCH_LIMITER")
    rate_limit = app.config.get("ORCH_RATE_LIMIT")

    def _limit_route(func):
        if limiter:
            return limiter.limit(rate_limit)(func)
        return func

    def _api_enabled() -> bool:
        return os.getenv("ORCH_ENABLE_API", "1") == "1"

    def _auth_required() -> bool:
        if os.getenv("ORCH_ENV", "development").lower() == "production":
            return True
        return os.getenv("ORCH_REQUIRE_BEARER", "1") == "1"

    def require_bearer() -> Tuple[bool, Dict[str, Any] | None]:
        if not _auth_required():
            return True, None
        token = os.getenv("ORCH_BEARER_TOKEN", "")
        got = request.headers.get("Authorization", "")
        if not token or got != f"Bearer {token}":
            return False, {"error": {"message": "Unauthorized", "type": "auth_error", "code": 401}}
        return True, None

    def _resolve_orchestrator_response(messages: List[Dict[str, str]], trace_id: str | None):
        orchestrator = current_app.config["ORCH_ORCHESTRATOR"]
        orch_mode = os.getenv("ORCH_ORCHESTRATOR_MODE", "basic")

        if orch_mode == "advanced":
            result = orchestrator.handle(messages, trace_id=trace_id)
            assistant_content = result["assistant_content"]
            model_decision = result.get("model_decision")
            tool_result = result.get("tool_result")
            route_decision = result.get("route_decision")
            intent_decision = result.get("intent_decision")
            semantic_candidates = result.get("semantic_candidates") or []
        else:
            use_llm = os.getenv("ORCH_LLM_ENABLED", "0") == "1"
            model_decision = None
            tool_result = None
            route_decision = None
            intent_decision = None
            semantic_candidates = []
            if use_llm:
                provider = get_provider()
                llm_response = provider.generate(messages)
                assistant_content = llm_response.content
                if trace_id:
                    tracer = get_tracer()
                    tracer.record_step(
                        trace_id,
                        "llm_provider",
                        {
                            "provider": llm_response.provider,
                            "model": llm_response.model,
                            "latency_ms": llm_response.latency_ms,
                            "output_chars": len(llm_response.content),
                            "attempts": llm_response.attempts,
                            "truncated": llm_response.truncated,
                            "timeout_sec": int(os.getenv("ORCH_LLM_TIMEOUT_SEC", "30")),
                            "network_enabled": os.getenv("ORCH_LLM_NETWORK_ENABLED", "0") == "1",
                        },
                    )
            else:
                last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
                content = last.get("content", "")
                assistant_content = build_demo_response(content)

        return assistant_content, route_decision, intent_decision, model_decision, tool_result, semantic_candidates

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "orchestrators_v2"}

    @app.get("/ready")
    def ready():
        if not _api_enabled():
            return {"status": "disabled", "service": "orchestrators_v2"}, 503

        if os.getenv("ORCH_LLM_ENABLED", "0") == "1":
            provider = get_provider()
            ok, reason = provider.health_check()
            if not ok:
                return {
                    "status": "unready",
                    "service": "orchestrators_v2",
                    "reason": reason,
                }, 503

        return {"status": "ready", "service": "orchestrators_v2"}

    @app.get("/metrics")
    def metrics():
        if os.getenv("ORCH_METRICS_ENABLED", "1") != "1":
            return {"status": "disabled", "service": "orchestrators_v2"}, 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401
        registry = current_app.config["ORCH_METRICS_REGISTRY"]
        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

    @app.post("/echo")
    def echo():
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401
        data = request.get_json(force=True, silent=True) or {}
        message = data.get("message", "")
        return jsonify({"echo": message}), 200

    @app.post("/v1/audit/verify")
    def audit_verify():
        if not _api_enabled():
            return jsonify({"error": {"message": "API disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        payload = request.get_json(force=True, silent=True) or {}
        trace_id = payload.get("trace_id")
        if not trace_id:
            return jsonify({"error": {"message": "trace_id required", "type": "invalid_request", "code": 400}}), 400

        tracer = get_tracer()
        steps = tracer.get_trace_steps(trace_id)
        policy_snapshot = load_policy_snapshot()

        policy_hash_current = policy_snapshot.get("policy_hash")
        policy_hash_trace = None
        policy_steps = []
        for step in steps:
            if step.get("step_type") == "policy_snapshot":
                policy_hash_trace = step.get("payload", {}).get("policy_hash")
                policy_steps.append(step)

        valid = bool(policy_hash_trace and policy_hash_current and policy_hash_trace == policy_hash_current)
        return jsonify({
            "trace_id": trace_id,
            "valid": valid,
            "policy_hash_current": policy_hash_current,
            "policy_hash_trace": policy_hash_trace,
            "policy_path": policy_snapshot.get("policy_path"),
            "policy_enforced": policy_snapshot.get("policy_enforced"),
            "policy_steps": policy_steps,
        }), 200

    @app.get("/v1/trust/events")
    @_limit_route
    def trust_events():
        if not _api_enabled() or not trust_panel_enabled():
            return jsonify({"error": {"message": "Trust panel disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        limit = request.args.get("limit")
        step_type = request.args.get("step_type")
        trace_id = request.args.get("trace_id")
        debug = request.args.get("debug") == "1"
        step_types = [s.strip() for s in step_type.split(",")] if step_type else None
        limit_value = int(limit) if limit and limit.isdigit() else None

        result = list_trust_events(
            limit=limit_value,
            step_types=step_types,
            trace_id=trace_id,
            debug=debug,
        )
        return jsonify(result), 200

    @app.get("/v1/trust/trace/<trace_id>")
    @_limit_route
    def trust_trace(trace_id: str):
        if not _api_enabled() or not trust_panel_enabled():
            return jsonify({"error": {"message": "Trust panel disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        debug = request.args.get("debug") == "1"
        report = get_trace_report(trace_id, debug=debug)
        if "error" in report:
            return jsonify({"error": {"message": report["error"], "type": "validation_error", "code": 400}}), 400
        return jsonify(report), 200

    @app.get("/v1/trust/verify/<trace_id>")
    @_limit_route
    def trust_verify(trace_id: str):
        if not _api_enabled() or not trust_panel_enabled():
            return jsonify({"error": {"message": "Trust panel disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        expected_hash = request.args.get("expected_hash")
        result = verify_trace_chain(trace_id, expected_hash=expected_hash)
        if "error" in result:
            return jsonify({"error": {"message": result["error"], "type": "validation_error", "code": 400}}), 400
        return jsonify(result), 200

    @app.post("/v1/chat/completions")
    @_limit_route
    def chat_completions():
        if not _api_enabled():
            return jsonify({"error": {"message": "API disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        payload = request.get_json(force=True, silent=False) or {}
        tracer = get_tracer()
        trace_handle = tracer.start_trace({
            "route": "/v1/chat/completions",
            "stream": bool(payload.get("stream", False)),
            "request_id": getattr(g, "request_id", None),
        })
        trace_id = trace_handle.trace_id if trace_handle else None

        messages = payload.get("messages", [])
        last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
        content = last.get("content", "")
        auth_header = request.headers.get("Authorization", "")
        user_id_hash = (
            hashlib.sha256(auth_header.encode()).hexdigest()[:16]
            if auth_header
            else "anonymous"
        )
        conversation_id = request.headers.get("X-Conversation-ID")
        memory_decision = evaluate_memory_capture(
            user_message=content,
            conversation_id=conversation_id,
            user_id_hash=user_id_hash,
            trace_id=trace_id,
        )

        try:
            assistant_content, route_decision, intent_decision, model_decision, tool_result, semantic_candidates = _resolve_orchestrator_response(messages, trace_id)
        except Exception as exc:
            return jsonify({
                "error": {
                    "message": f"LLM provider error: {exc}",
                    "type": "provider_error",
                    "code": 502,
                },
                "memory_decision": memory_decision,
            }), 502

        if trace_id and semantic_candidates:
            tracer.record_step(
                trace_id,
                "semantic_router",
                {
                    "candidates": [
                        {"tool": candidate.tool, "score": candidate.score}
                        for candidate in semantic_candidates
                    ],
                    "decision": route_decision.__dict__ if route_decision else None,
                },
            )

        expose_intent = os.getenv("ORCH_INTENT_DECISION_EXPOSE", "0") == "1" or request.args.get("debug") == "1"

        response_payload = {
            "id": "orch_v2_stub",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": assistant_content},
                "finish_reason": "stop"
            }],
            "request_id": trace_id or getattr(g, "request_id", None),
            "memory_decision": memory_decision,
            "route_decision": route_decision.__dict__ if route_decision else None,
            "model_decision": model_decision.__dict__ if model_decision else None,
            "tool_result": tool_result,
        }
        if expose_intent:
            response_payload["intent_decision"] = intent_decision.__dict__ if intent_decision else None
        return jsonify(response_payload)

    @app.get("/v1/agents")
    def agents_list():
        if not _api_enabled():
            return jsonify({"error": {"message": "API disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        agents = list_agents()
        return jsonify({"count": len(agents), "agents": agents}), 200

    @app.get("/v1/agents/<name>")
    def agents_get(name: str):
        if not _api_enabled():
            return jsonify({"error": {"message": "API disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        agent = get_agent(name)
        if not agent:
            return jsonify({"error": {"message": "Agent not found", "type": "not_found", "code": 404}}), 404

        return jsonify({
            "name": agent.name,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
            "tools": agent.tools,
            "metadata": agent.metadata,
        }), 200

    @app.post("/v1/agents/<name>/chat")
    @_limit_route
    def agents_chat(name: str):
        if not _api_enabled():
            return jsonify({"error": {"message": "API disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        agent = get_agent(name)
        if not agent:
            return jsonify({"error": {"message": "Agent not found", "type": "not_found", "code": 404}}), 404

        payload = request.get_json(force=True, silent=False) or {}
        messages = payload.get("messages", [])
        if not messages:
            return jsonify({"error": {"message": "Messages required", "type": "invalid_request", "code": 400}}), 400

        tracer = get_tracer()
        trace_handle = tracer.start_trace({
            "route": f"/v1/agents/{name}/chat",
            "agent": agent.name,
            "stream": False,
            "request_id": getattr(g, "request_id", None),
        })
        trace_id = trace_handle.trace_id if trace_handle else None

        last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
        content = last.get("content", "")
        auth_header = request.headers.get("Authorization", "")
        user_id_hash = (
            hashlib.sha256(auth_header.encode()).hexdigest()[:16]
            if auth_header
            else "anonymous"
        )
        conversation_id = request.headers.get("X-Conversation-ID")
        memory_decision = evaluate_memory_capture(
            user_message=content,
            conversation_id=conversation_id,
            user_id_hash=user_id_hash,
            trace_id=trace_id,
        )

        agent_messages = inject_agent_prompt(messages, agent, trace_id=trace_id)
        try:
            assistant_content, route_decision, model_decision, tool_result, semantic_candidates = _resolve_orchestrator_response(agent_messages)
        except Exception as exc:
            return jsonify({
                "error": {
                    "message": f"LLM provider error: {exc}",
                    "type": "provider_error",
                    "code": 502,
                },
                "memory_decision": memory_decision,
            }), 502

        if trace_id and semantic_candidates:
            tracer.record_step(
                trace_id,
                "semantic_router",
                {
                    "candidates": [
                        {"tool": candidate.tool, "score": candidate.score}
                        for candidate in semantic_candidates
                    ],
                    "decision": route_decision.__dict__ if route_decision else None,
                },
            )

        return jsonify({
            "id": "orch_v2_agent",
            "object": "chat.completion",
            "agent": agent.name,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": assistant_content},
                "finish_reason": "stop"
            }],
            "request_id": trace_id or getattr(g, "request_id", None),
            "memory_decision": memory_decision,
            "route_decision": route_decision.__dict__ if route_decision else None,
            "model_decision": model_decision.__dict__ if model_decision else None,
            "tool_result": tool_result,
        }), 200

    @app.post("/v1/tools/execute")
    @_limit_route
    def tools_execute():
        if not _api_enabled():
            return jsonify({"error": {"message": "API disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        payload = request.get_json(force=True, silent=False) or {}
        tool_name = payload.get("name")
        tool_args = payload.get("args") or {}
        approval_token = payload.get("approval_token")
        if not tool_name:
            return jsonify({"error": {"message": "Tool name required", "type": "validation_error", "code": 400}}), 400

        orchestrator = current_app.config["ORCH_ORCHESTRATOR"]
        result = orchestrator.execute_tool_guarded(
            tool_name,
            tool_args,
            approval_token=approval_token,
            trace_id=getattr(g, "request_id", None),
        )
        return jsonify({"result": result})

    @app.post("/v1/tools/approve")
    @_limit_route
    def tools_approve():
        if not _api_enabled():
            return jsonify({"error": {"message": "API disabled", "type": "service_unavailable", "code": 503}}), 503
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401

        payload = request.get_json(force=True, silent=False) or {}
        tool_name = payload.get("name")
        tool_args = payload.get("args") or {}
        ttl_seconds = payload.get("ttl_seconds")
        if not tool_name:
            return jsonify({"error": {"message": "Tool name required", "type": "validation_error", "code": 400}}), 400

        approvals = ToolApprovalStore()
        approval = approvals.issue(tool_name, tool_args, ttl_seconds=ttl_seconds)
        return jsonify({
            "approval_id": approval.approval_id,
            "tool": approval.tool_name,
            "args_hash": approval.args_hash,
            "created_at": approval.created_at,
            "expires_at": approval.expires_at,
            "status": approval.status,
        }), 200

    return Blueprint("orchestrator_api", __name__)
