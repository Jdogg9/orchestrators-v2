from __future__ import annotations

import hashlib
import os
from typing import Tuple, Any, Dict, List

from flask import Blueprint, Response, current_app, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.agents import get_agent, inject_agent_prompt, list_agents
from src.llm_provider import get_provider
from src.orchestrator_memory import evaluate_memory_capture
from src.tracer import get_tracer


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

    def _resolve_orchestrator_response(messages: List[Dict[str, str]]):
        orchestrator = current_app.config["ORCH_ORCHESTRATOR"]
        orch_mode = os.getenv("ORCH_ORCHESTRATOR_MODE", "basic")

        if orch_mode == "advanced":
            result = orchestrator.handle(messages)
            assistant_content = result["assistant_content"]
            model_decision = result.get("model_decision")
            tool_result = result.get("tool_result")
            route_decision = result.get("route_decision")
            semantic_candidates = result.get("semantic_candidates") or []
        else:
            use_llm = os.getenv("ORCH_LLM_ENABLED", "0") == "1"
            model_decision = None
            tool_result = None
            route_decision = None
            semantic_candidates = []
            if use_llm:
                provider = get_provider()
                llm_response = provider.generate(messages)
                assistant_content = llm_response.content
            else:
                last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
                content = last.get("content", "")
                assistant_content = f"[ORCHESTRATORS_V2 stub] You said: {content}"

        return assistant_content, route_decision, model_decision, tool_result, semantic_candidates

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
            assistant_content, route_decision, model_decision, tool_result, semantic_candidates = _resolve_orchestrator_response(messages)
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
        })

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

        agent_messages = inject_agent_prompt(messages, agent)
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
        if not tool_name:
            return jsonify({"error": {"message": "Tool name required", "type": "validation_error", "code": 400}}), 400

        orchestrator = current_app.config["ORCH_ORCHESTRATOR"]
        result = orchestrator.registry.execute(tool_name, **tool_args)
        return jsonify({"result": result})

    return Blueprint("orchestrator_api", __name__)
