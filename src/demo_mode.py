from __future__ import annotations

import os
from typing import Optional


def _heuristic_intent(text: str) -> str:
    lowered = (text or "").lower()
    if "calc" in lowered:
        return "safe_calc"
    if "echo" in lowered:
        return "echo"
    if lowered.strip():
        return "chat"
    return "unknown"


def build_demo_response(
    user_input: str,
    route_decision: Optional[object] = None,
    intent_decision: Optional[object] = None,
) -> str:
    provider = os.getenv("ORCH_LLM_PROVIDER", "ollama")
    model = os.getenv("ORCH_MODEL_CHAT", "qwen2.5:3b")
    network_enabled = os.getenv("ORCH_LLM_NETWORK_ENABLED", "0") == "1"

    intent = None
    if intent_decision is not None:
        intent = getattr(intent_decision, "intent_id", None)
    intent = intent or _heuristic_intent(user_input)

    tool = None
    if route_decision is not None:
        tool = getattr(route_decision, "tool", None)
    tool = tool or (intent if intent in {"safe_calc", "echo"} else None)

    lines = [
        "[ORCHESTRATORS_V2 demo mode]",
        "LLM enabled: false",
        f"Intent (heuristic): {intent}",
        f"Route (heuristic): {tool or 'none'}",
        "Tool execution requires execute_tool_guarded; unsafe tools require approval.",
        f"If LLM enabled: provider={provider}, model={model}, network_enabled={network_enabled}",
        "Receipts: set ORCH_TRACE_ENABLED=1 to emit trace steps.",
    ]
    return "\n".join(lines)