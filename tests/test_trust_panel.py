import os

from src.tracer import TraceStore
from src.trust_panel import sanitize_payload, list_trust_events, get_trace_report, verify_trace_chain


def test_trust_panel_sanitizes_sensitive_fields():
    payload = {
        "authorization": "Bearer sk-test-abcdef1234567890",
        "api_key": "sk-test-abcdef1234567890",
        "nested": {"token": "ghp_abcdefghijklmnopqrstuvwxyz0123456789abcd"},
        "note": "contact me at user@example.com",
    }
    sanitized, redactions = sanitize_payload(payload)

    assert redactions >= 3
    assert sanitized["authorization"] == "<redacted>"
    assert sanitized["api_key"] == "<redacted>"
    assert sanitized["nested"]["token"] == "<redacted>"
    assert "<redacted>" in sanitized["note"]


def test_trust_panel_chain_verification(tmp_path):
    trace_db = tmp_path / "trace.db"
    os.environ["ORCH_TRACE_DB_PATH"] = str(trace_db)

    store = TraceStore(db_path=str(trace_db), enabled=True)
    trace = store.start_trace({"route": "/v1/chat/completions"})
    assert trace is not None

    store.record_step(trace.trace_id, "tool_approval", {"tool": "echo", "approved": True})
    store.record_step(trace.trace_id, "llm_provider", {"model": "demo", "latency_ms": 10})

    report = get_trace_report(trace.trace_id)
    assert report["step_count"] == 2
    chain_hash = report["chain_hash"]

    verification = verify_trace_chain(trace.trace_id, expected_hash=chain_hash)
    assert verification["verified"] is True

    events = list_trust_events(trace_id=trace.trace_id)
    assert events["count"] == 2
