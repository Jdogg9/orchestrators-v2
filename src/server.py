import hashlib
import os
import time
import uuid
from flask import Flask, request, jsonify, g
from dotenv import load_dotenv

from src.orchestrator_memory import evaluate_memory_capture
from src.llm_provider import get_provider
from src.tracer import get_tracer

load_dotenv()

app = Flask(__name__)


@app.before_request
def start_request():
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    g.request_start = time.time()


@app.after_request
def finalize_request(response):
    request_id = getattr(g, "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
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

@app.post("/echo")
def echo():
    """Echo endpoint for testing - returns message field as 'echo' response"""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    return jsonify({"echo": message}), 200

@app.post("/v1/chat/completions")
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
    
    use_llm = os.getenv("ORCH_LLM_ENABLED", "0") == "1"
    if use_llm:
        try:
            provider = get_provider()
            llm_response = provider.generate(messages)
            assistant_content = llm_response.content
        except Exception as exc:
            return jsonify({
                "error": {
                    "message": f"LLM provider error: {exc}",
                    "type": "provider_error",
                    "code": 502,
                },
                "memory_decision": memory_decision,
            }), 502
    else:
        # Minimal stub: echo last user message. Replace with real routing/provider calls.
        assistant_content = f"[ORCHESTRATORS_V2 stub] You said: {content}"

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
    })

if __name__ == "__main__":
    port = int(os.getenv("ORCH_PORT", "8088"))
    host = os.getenv("ORCH_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False)
