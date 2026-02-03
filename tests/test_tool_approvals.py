from datetime import datetime, timedelta, timezone

from src.approval_store import ToolApprovalStore, hash_tool_args


def test_tool_approval_consumes_once(tmp_path):
    db_path = tmp_path / "tool_approvals.db"
    store = ToolApprovalStore(db_path=str(db_path))

    approval = store.issue("python_exec", {"code": "print(1)"}, ttl_seconds=60)
    approved, reason, _ = store.validate_and_consume(
        approval.approval_id,
        "python_exec",
        approval.args_hash,
    )
    assert approved is True
    assert reason == "approved"

    approved_again, reason_again, _ = store.validate_and_consume(
        approval.approval_id,
        "python_exec",
        approval.args_hash,
    )
    assert approved_again is False
    assert reason_again == "already_consumed"


def test_tool_approval_expires(tmp_path):
    db_path = tmp_path / "tool_approvals.db"
    store = ToolApprovalStore(db_path=str(db_path))

    approval = store.issue("python_exec", {"code": "print(1)"}, ttl_seconds=1)

    # Force expiry by manipulating stored record.
    expired_at = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    import sqlite3
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE tool_approvals SET expires_at = ? WHERE approval_id = ?",
            (expired_at, approval.approval_id),
        )
        conn.commit()

    approved, reason, _ = store.validate_and_consume(
        approval.approval_id,
        "python_exec",
        approval.args_hash,
    )
    assert approved is False
    assert reason == "expired"


def test_tool_approval_args_hash_mismatch(tmp_path):
    db_path = tmp_path / "tool_approvals.db"
    store = ToolApprovalStore(db_path=str(db_path))

    approval = store.issue("python_exec", {"code": "print(1)"}, ttl_seconds=60)
    mismatch_hash = hash_tool_args({"code": "print(2)"})

    approved, reason, _ = store.validate_and_consume(
        approval.approval_id,
        "python_exec",
        mismatch_hash,
    )
    assert approved is False
    assert reason == "args_hash_mismatch"
