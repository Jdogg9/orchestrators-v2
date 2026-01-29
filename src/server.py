import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

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

@app.post("/v1/chat/completions")
def chat_completions():
    ok, err = require_bearer()
    if not ok:
        return jsonify(err), 401
    
    payload = request.get_json(force=True, silent=False)
    # Minimal stub: echo last user message. Replace with real routing/provider calls.
    messages = payload.get("messages", [])
    last = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    content = last.get("content", "")
    
    return jsonify({
        "id": "orch_v2_stub",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": f"[ORCHESTRATORS_V2 stub] You said: {content}"},
            "finish_reason": "stop"
        }]
    })

if __name__ == "__main__":
    port = int(os.getenv("ORCH_PORT", "8088"))
    app.run(host="127.0.0.1", port=port, debug=False)
