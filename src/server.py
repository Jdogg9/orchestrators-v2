import hashlib
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from src.orchestrator_memory import evaluate_memory_capture
from src.tracer import get_tracer

load_dotenv()

app = Flask(__name__)

def require_bearer():
    if os.getenv("ORCH_REQUIRE_BEARER", "0") != "1":
        return True, None
    token = os.getenv("ORCH_BEARER_TOKEN", "")
    got = request.headers.get("Authorization", "")
    if not token or got != f"Bearer {token}":
        return False, {"error": {"message": "Unauthorized", "type": "auth_error", "code": 401}}
    return True, None

@app.get("/health")
def health():
    return {"status": "ok", "service": "orchestrators_v2"}

@app.post("/echo")
def echo():
    """Echo endpoint for testing - returns message field as 'echo' response"""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    return jsonify({"echo": message}), 200

@app.post("/v1/chat/completions")
def chat_completions():
    ok, err = require_bearer()
    if not ok:
        return jsonify(err), 401
    
    payload = request.get_json(force=True, silent=False)
    tracer = get_tracer()
    trace_handle = tracer.start_trace({
        "route": "/v1/chat/completions",
        "stream": bool(payload.get("stream", False)),
    })
    trace_id = trace_handle.trace_id if trace_handle else None

    # Minimal stub: echo last user message. Replace with real routing/provider calls.
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
    
    return jsonify({
        "id": "orch_v2_stub",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": f"[ORCHESTRATORS_V2 stub] You said: {content}"},
            "finish_reason": "stop"
        }],
        "memory_decision": memory_decision,
    })

if __name__ == "__main__":
    port = int(os.getenv("ORCH_PORT", "8088"))
    app.run(host="127.0.0.1", port=port, debug=False)
