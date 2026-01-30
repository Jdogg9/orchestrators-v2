import hashlib
from typing import Optional, Dict, Any

from src.memory import capture_candidate_memory, should_capture_user_message, _record_memory_write_decision


def evaluate_memory_capture(
    user_message: str,
    conversation_id: Optional[str],
    user_id_hash: Optional[str],
    scope: str = "global",
    source: str = "chat",
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not user_id_hash:
        user_id_hash = "anonymous"

    write_policy = _get_write_policy()
    explicit_intent = should_capture_user_message(user_message, write_policy)

    if write_policy == "strict" and not explicit_intent:
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:no_explicit_intent",
            explicit_intent=False,
            write_policy=write_policy,
            scrub_applied=False,
            ttl_minutes=_get_ttl_minutes(),
            scope=scope,
            source=source,
        )
        return {
            "decision": "deny",
            "reason": "deny:no_explicit_intent",
            "candidate_id": None,
        }

    candidate_id = capture_candidate_memory(
        user_id_hash=user_id_hash,
        conversation_id=conversation_id,
        text=user_message,
        scope=scope,
        source=source,
        trace_id=trace_id,
    )

    if candidate_id:
        return {
            "decision": "allow",
            "reason": "allow:explicit_intent" if write_policy == "strict" else "allow:capture_only",
            "candidate_id": candidate_id,
            "candidate_id_hash": hashlib.sha256(candidate_id.encode()).hexdigest()[:12],
        }

    return {
        "decision": "deny",
        "reason": "deny:policy_write_disabled",
        "candidate_id": None,
    }


def _get_write_policy() -> str:
    import os

    return os.getenv("ORCH_MEMORY_WRITE_POLICY", "off")


def _get_ttl_minutes() -> int:
    import os

    return int(os.getenv("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180"))
