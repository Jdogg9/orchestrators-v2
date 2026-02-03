from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DEFAULT_APPROVAL_DB = "instance/tool_approvals.db"


def hash_tool_args(args: Dict[str, Any]) -> str:
    payload = json.dumps(args or {}, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256(payload)


def _sha256(payload: str) -> str:
    import hashlib

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ToolApproval:
    approval_id: str
    tool_name: str
    args_hash: str
    created_at: str
    expires_at: str
    consumed_at: Optional[str]
    status: str


class ToolApprovalStore:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or os.getenv("ORCH_TOOL_APPROVAL_DB_PATH", DEFAULT_APPROVAL_DB)
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_approvals (
                    approval_id TEXT PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    args_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            conn.commit()

    def issue(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolApproval:
        ttl_seconds = ttl_seconds or int(os.getenv("ORCH_TOOL_APPROVAL_TTL_SEC", "900"))
        now = datetime.now(timezone.utc)
        created_at = now.isoformat()
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        approval_id = str(uuid.uuid4())
        args_hash = hash_tool_args(args)
        payload = json.dumps(metadata or {}, separators=(",", ":"))

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tool_approvals (
                    approval_id, tool_name, args_hash, created_at, expires_at, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (approval_id, tool_name, args_hash, created_at, expires_at, "pending", payload),
            )
            conn.commit()

        return ToolApproval(
            approval_id=approval_id,
            tool_name=tool_name,
            args_hash=args_hash,
            created_at=created_at,
            expires_at=expires_at,
            consumed_at=None,
            status="pending",
        )

    def validate_and_consume(
        self,
        approval_id: str,
        tool_name: str,
        args_hash: str,
    ) -> Tuple[bool, str, Optional[ToolApproval]]:
        if not approval_id:
            return False, "missing_approval", None

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM tool_approvals WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()

            if not row:
                return False, "unknown_approval", None

            status = row["status"]
            if status != "pending":
                return False, "already_consumed", self._row_to_approval(row)

            if row["tool_name"] != tool_name:
                return False, "tool_mismatch", self._row_to_approval(row)

            if row["args_hash"] != args_hash:
                return False, "args_hash_mismatch", self._row_to_approval(row)

            expires_at = datetime.fromisoformat(row["expires_at"])
            now = datetime.now(timezone.utc)
            if expires_at <= now:
                return False, "expired", self._row_to_approval(row)

            consumed_at = now.isoformat()
            conn.execute(
                """
                UPDATE tool_approvals
                SET status = ?, consumed_at = ?
                WHERE approval_id = ?
                """,
                ("consumed", consumed_at, approval_id),
            )
            conn.commit()

            approval = ToolApproval(
                approval_id=approval_id,
                tool_name=tool_name,
                args_hash=args_hash,
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                consumed_at=consumed_at,
                status="consumed",
            )
            return True, "approved", approval

    @staticmethod
    def _row_to_approval(row: sqlite3.Row) -> ToolApproval:
        return ToolApproval(
            approval_id=row["approval_id"],
            tool_name=row["tool_name"],
            args_hash=row["args_hash"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            consumed_at=row["consumed_at"],
            status=row["status"],
        )


def approval_enforced() -> bool:
    return os.getenv("ORCH_TOOL_APPROVAL_ENFORCE", "1") == "1"