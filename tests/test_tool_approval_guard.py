from datetime import datetime, timedelta, timezone
import sqlite3

from src.approval_store import ToolApprovalStore
from src.orchestrator import Orchestrator


def _fake_executor(tool_name, tool_args, trace_id=None):
    return {"status": "ok", "tool": tool_name, "result": tool_args}


def test_execute_tool_guarded_blocks_missing_approval(tmp_path):
    store = ToolApprovalStore(db_path=str(tmp_path / "tool_approvals.db"))
    orch = Orchestrator()

    result = orch.execute_tool_guarded(
        "python_exec",
        {"code": "print(1)"},
        approval_token=None,
        tool_executor=_fake_executor,
        approval_store=store,
    )

    assert result["status"] == "error"
    assert result["error"] == "approval_required"
    assert result["approval_reason"] == "missing_approval"


def test_execute_tool_guarded_blocks_args_mismatch(tmp_path):
    store = ToolApprovalStore(db_path=str(tmp_path / "tool_approvals.db"))
    orch = Orchestrator()

    approval = store.issue("python_exec", {"code": "print(1)"}, ttl_seconds=60)

    result = orch.execute_tool_guarded(
        "python_exec",
        {"code": "print(2)"},
        approval_token=approval.approval_id,
        tool_executor=_fake_executor,
        approval_store=store,
    )

    assert result["status"] == "error"
    assert result["error"] == "approval_required"
    assert result["approval_reason"] == "args_hash_mismatch"


def test_execute_tool_guarded_blocks_expired(tmp_path):
    store = ToolApprovalStore(db_path=str(tmp_path / "tool_approvals.db"))
    orch = Orchestrator()

    approval = store.issue("python_exec", {"code": "print(1)"}, ttl_seconds=60)
    expired_at = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()

    with sqlite3.connect(str(tmp_path / "tool_approvals.db")) as conn:
        conn.execute(
            "UPDATE tool_approvals SET expires_at = ? WHERE approval_id = ?",
            (expired_at, approval.approval_id),
        )
        conn.commit()

    result = orch.execute_tool_guarded(
        "python_exec",
        {"code": "print(1)"},
        approval_token=approval.approval_id,
        tool_executor=_fake_executor,
        approval_store=store,
    )

    assert result["status"] == "error"
    assert result["error"] == "approval_required"
    assert result["approval_reason"] == "expired"


def test_execute_tool_guarded_consumes_once(tmp_path):
    store = ToolApprovalStore(db_path=str(tmp_path / "tool_approvals.db"))
    orch = Orchestrator()

    approval = store.issue("python_exec", {"code": "print(1)"}, ttl_seconds=60)

    first = orch.execute_tool_guarded(
        "python_exec",
        {"code": "print(1)"},
        approval_token=approval.approval_id,
        tool_executor=_fake_executor,
        approval_store=store,
    )
    assert first["status"] == "ok"

    second = orch.execute_tool_guarded(
        "python_exec",
        {"code": "print(1)"},
        approval_token=approval.approval_id,
        tool_executor=_fake_executor,
        approval_store=store,
    )
    assert second["status"] == "error"
    assert second["error"] == "approval_required"
    assert second["approval_reason"] == "already_consumed"
