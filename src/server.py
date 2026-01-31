import hashlib
import logging
import os
import time
import uuid
import json
from flask import Flask, request, jsonify, g, Response
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.orchestrator_memory import evaluate_memory_capture
from src.orchestrator import Orchestrator
from src.llm_provider import get_provider
from src.observability import init_otel, get_current_trace_context
from src.agents import get_agent, list_agents, inject_agent_prompt
from src.tracer import get_tracer

load_dotenv()

app = Flask(__name__)
init_otel(app)

MAX_REQUEST_BYTES = int(os.getenv("ORCH_MAX_REQUEST_BYTES", "1048576"))
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

LOG_LEVEL = os.getenv("ORCH_LOG_LEVEL", "INFO").upper()
LOG_JSON = os.getenv("ORCH_LOG_JSON", "1") == "1"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - logging
        base = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": int(record.created * 1000),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            base.update(record.extra)
        return json.dumps(base, separators=(",", ":"))


logger = logging.getLogger("orchestrators_v2")
logger.setLevel(LOG_LEVEL)
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter() if LOG_JSON else logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)

RATE_LIMIT_ENABLED = os.getenv("ORCH_RATE_LIMIT_ENABLED", "1") == "1"
RATE_LIMIT = os.getenv("ORCH_RATE_LIMIT", "60 per minute")
RATE_LIMIT_STORAGE_URL = os.getenv("ORCH_RATE_LIMIT_STORAGE_URL")
limiter = (
    Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[RATE_LIMIT],
        storage_uri=RATE_LIMIT_STORAGE_URL,
    )
    if RATE_LIMIT_ENABLED
    else None
)

METRICS_REGISTRY = CollectorRegistry(auto_describe=True)
REQUEST_COUNT = Counter(
    "orch_requests_total",
    "Total requests",
    ["route", "method", "status"],
    registry=METRICS_REGISTRY,
)
REQUEST_LATENCY = Histogram(
    "orch_request_latency_seconds",
    "Request latency",
    ["route", "method"],
    registry=METRICS_REGISTRY,
)
ERROR_COUNT = Counter(
    "orch_errors_total",
    "Total errors",
    ["route", "method", "status"],
    registry=METRICS_REGISTRY,
)

orchestrator = Orchestrator()


@app.before_request
def start_request():
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    g.request_start = time.time()
    otel_context = get_current_trace_context()
    if otel_context:
        g.otel_trace_id = otel_context.get("trace_id")
        g.otel_span_id = otel_context.get("span_id")
    g.otel_traceparent = request.headers.get("traceparent")


def _trace_metadata(base: dict) -> dict:
    metadata = dict(base)
    request_id = getattr(g, "request_id", None)
    if request_id:
        metadata["request_id"] = request_id

    otel_trace_id = getattr(g, "otel_trace_id", None)
    if otel_trace_id:
        metadata["otel_trace_id"] = otel_trace_id

    otel_span_id = getattr(g, "otel_span_id", None)
    if otel_span_id:
        metadata["otel_span_id"] = otel_span_id

    traceparent = getattr(g, "otel_traceparent", None)
    if traceparent:
        metadata["traceparent"] = traceparent

    return metadata


@app.after_request
def finalize_request(response):
    request_id = getattr(g, "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    route = request.path
    method = request.method
    status = str(response.status_code)
    duration = time.time() - getattr(g, "request_start", time.time())
    REQUEST_COUNT.labels(route, method, status).inc()
    REQUEST_LATENCY.labels(route, method).observe(duration)
    if response.status_code >= 500:
        ERROR_COUNT.labels(route, method, status).inc()

    logger.info(
        "request",
        extra={
            "extra": {
                "request_id": request_id,
                "route": route,
                "method": method,
                "status": response.status_code,
                "latency_ms": int(duration * 1000),
            }
        },
    )
    return response

def require_bearer():
    if os.getenv("ORCH_REQUIRE_BEARER", "0") != "1":
        return True, None
    token = os.getenv("ORCH_BEARER_TOKEN", "")
    got = request.headers.get("Authorization", "")
    if not token or got != f"Bearer {token}":
        return False, {"error": {"message": "Unauthorized", "type": "auth_error", "code": 401}}
    return True, None


def _api_enabled() -> bool:
    return os.getenv("ORCH_ENABLE_API", "1") == "1"

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
    if os.getenv("ORCH_REQUIRE_BEARER", "0") == "1":
        ok, err = require_bearer()
        if not ok:
            return jsonify(err), 401
    return Response(generate_latest(METRICS_REGISTRY), mimetype=CONTENT_TYPE_LATEST)

@app.post("/echo")
def echo():
    """Echo endpoint for testing - returns message field as 'echo' response"""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    return jsonify({"echo": message}), 200

def _limit_route(func):
    if limiter:
        return limiter.limit(RATE_LIMIT)(func)
    return func


def _resolve_orchestrator_response(messages):
    orch_mode = os.getenv("ORCH_ORCHESTRATOR_MODE", "basic")
    if orch_mode == "advanced":
        result = orchestrator.handle(messages)
        assistant_content = result["assistant_content"]
        model_decision = result.get("model_decision")
        tool_result = result.get("tool_result")
        route_decision = result.get("route_decision")
    else:
        use_llm = os.getenv("ORCH_LLM_ENABLED", "0") == "1"
        model_decision = None
        tool_result = None
        route_decision = None
        if use_llm:
            provider = get_provider()
            llm_response = provider.generate(messages)
            assistant_content = llm_response.content
        else:
            last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
            content = last.get("content", "")
            assistant_content = f"[ORCHESTRATORS_V2 stub] You said: {content}"

    return assistant_content, route_decision, model_decision, tool_result


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
    trace_handle = tracer.start_trace(_trace_metadata({
        "route": "/v1/chat/completions",
        "stream": bool(payload.get("stream", False)),
    }))
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
        assistant_content, route_decision, model_decision, tool_result = _resolve_orchestrator_response(messages)
    except Exception as exc:
        return jsonify({
            "error": {
                "message": f"LLM provider error: {exc}",
                "type": "provider_error",
                "code": 502,
            },
            "memory_decision": memory_decision,
        }), 502

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
    trace_handle = tracer.start_trace(_trace_metadata({
        "route": f"/v1/agents/{name}/chat",
        "agent": agent.name,
        "stream": False,
    }))
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
        assistant_content, route_decision, model_decision, tool_result = _resolve_orchestrator_response(agent_messages)
    except Exception as exc:
        return jsonify({
            "error": {
                "message": f"LLM provider error: {exc}",
                "type": "provider_error",
                "code": 502,
            },
            "memory_decision": memory_decision,
        }), 502

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

    result = orchestrator.registry.execute(tool_name, **tool_args)
    return jsonify({"result": result})

if __name__ == "__main__":
    port = int(os.getenv("ORCH_PORT", "8088"))
    host = os.getenv("ORCH_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False)
