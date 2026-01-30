import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

TRACE_ENABLED = os.getenv("ORCH_TRACE_ENABLED", "1") == "1"
DEFAULT_TRACE_DB = os.getenv("ORCH_TRACE_DB_PATH", "instance/trace.db")


@dataclass
class TraceHandle:
    trace_id: str


class TraceStore:
    def __init__(self, db_path: str = DEFAULT_TRACE_DB, enabled: bool = TRACE_ENABLED):
        self.db_path = db_path
        self.enabled = enabled
        if not self.enabled:
            return
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            self._ensure_trace_steps_schema(conn)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_trace_steps_schema(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trace_steps'")
        existing = cursor.fetchone()
        if not existing:
            cursor.execute(
                """
                CREATE TABLE trace_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    step_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            return

        cursor.execute("PRAGMA table_info(trace_steps)")
        columns = {row[1] for row in cursor.fetchall()}
        required = {"trace_id", "step_type", "step_json", "created_at"}
        if required.issubset(columns):
            return

        # Rebuild table if schema mismatched
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        legacy = f"trace_steps_legacy_{timestamp}"
        cursor.execute(f"ALTER TABLE trace_steps RENAME TO {legacy}")
        cursor.execute(
            """
            CREATE TABLE trace_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                step_type TEXT NOT NULL,
                step_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    def start_trace(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[TraceHandle]:
        if not self.enabled:
            return None
        trace_id = str(uuid.uuid4())
        payload = json.dumps(metadata or {})
        created_at = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO traces (id, created_at, metadata_json) VALUES (?, ?, ?)",
                (trace_id, created_at, payload),
            )
            conn.commit()
        return TraceHandle(trace_id=trace_id)

    def record_step(self, trace_id: str, step_type: str, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        created_at = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            self._ensure_trace_steps_schema(conn)
            conn.execute(
                """
                INSERT INTO trace_steps (trace_id, step_type, step_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (trace_id, step_type, json.dumps(payload), created_at),
            )
            conn.commit()

    def record_memory_write_decision(self, trace_id: str, **payload: Any) -> None:
        if not self.enabled or not trace_id:
            return
        self.record_step(trace_id, "memory_write_decision", payload)


_tracer: Optional[TraceStore] = None


def get_tracer() -> TraceStore:
    global _tracer
    if _tracer is None:
        _tracer = TraceStore()
    return _tracer
