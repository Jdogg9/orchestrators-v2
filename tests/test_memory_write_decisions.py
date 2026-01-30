import os
from pathlib import Path

import pytest

from src import memory
from src.orchestrator_memory import evaluate_memory_capture
from src.tracer import TraceStore


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCH_MEMORY_ENABLED", "0")
    monkeypatch.setenv("ORCH_MEMORY_CAPTURE_ENABLED", "0")
    monkeypatch.setenv("ORCH_MEMORY_WRITE_POLICY", "off")
    monkeypatch.setenv("ORCH_TRACE_ENABLED", "0")
    monkeypatch.setenv("ORCH_MEMORY_DB_PATH", str(tmp_path / "memory.db"))
    monkeypatch.setenv("ORCH_TRACE_DB_PATH", str(tmp_path / "trace.db"))
    yield


def test_decision_taxonomy_is_explicit():
    expected = {
        "allow:explicit_intent",
        "allow:dedupe_update",
        "allow:capture_only",
        "deny:feature_disabled",
        "deny:policy_write_disabled",
        "deny:no_explicit_intent",
        "deny:scrubbed_too_short",
        "deny:sensitive_content",
        "deny:error",
    }
    assert memory.ALLOWED_DECISION_REASONS == expected


def test_trace_steps_schema_idempotent(tmp_path):
    db_path = tmp_path / "trace.db"
    tracer = TraceStore(db_path=str(db_path), enabled=True)
    tracer._init_db()
    tracer._init_db()

    with tracer._get_conn() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(trace_steps)")}
    assert {"trace_id", "step_type", "step_json", "created_at"}.issubset(columns)


def test_deny_no_explicit_intent_is_side_effect_free(tmp_path, monkeypatch):
    monkeypatch.setenv("ORCH_MEMORY_ENABLED", "1")
    monkeypatch.setenv("ORCH_MEMORY_CAPTURE_ENABLED", "1")
    monkeypatch.setenv("ORCH_MEMORY_WRITE_POLICY", "strict")
    monkeypatch.setenv("ORCH_TRACE_ENABLED", "0")

    decision = evaluate_memory_capture(
        user_message="hello there",
        conversation_id="conv",
        user_id_hash="user",
    )

    assert decision["decision"] == "deny"
    assert decision["reason"] == "deny:no_explicit_intent"
    assert not Path(os.getenv("ORCH_MEMORY_DB_PATH")).exists()


def test_capture_strict_allows_explicit_intent(tmp_path, monkeypatch):
    monkeypatch.setenv("ORCH_MEMORY_ENABLED", "1")
    monkeypatch.setenv("ORCH_MEMORY_CAPTURE_ENABLED", "1")
    monkeypatch.setenv("ORCH_MEMORY_WRITE_POLICY", "strict")

    decision = evaluate_memory_capture(
        user_message="remember this: we deploy on Fridays",
        conversation_id="conv",
        user_id_hash="user",
    )

    assert decision["decision"] == "allow"
    assert decision["candidate_id"]
    db_path = Path(os.getenv("ORCH_MEMORY_DB_PATH"))
    assert db_path.exists()
