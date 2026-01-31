import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import text

try:
    from opentelemetry import trace as otel_trace
except ImportError:  # Optional dependency
    otel_trace = None

from src.db import get_engine

TRACE_ENABLED = os.getenv("ORCH_TRACE_ENABLED", "1") == "1"
DEFAULT_TRACE_DB = os.getenv("ORCH_TRACE_DB_PATH", "instance/trace.db")

OTEL_TRACE_STEP_KEYS = {
    "decision",
    "reason",
    "explicit_intent",
    "write_policy",
    "scope",
    "source",
    "candidate_id_hash",
    "tool_name",
    "route",
    "model",
    "status",
    "error_type",
}


@dataclass
class TraceHandle:
    trace_id: str


class TraceStore:
    def __init__(self, db_path: str = DEFAULT_TRACE_DB, enabled: bool = TRACE_ENABLED):
        self.db_path = db_path
        self.enabled = enabled
        self.engine = get_engine()
        if not self.enabled:
            return
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        if self.engine:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS traces (
                            id TEXT PRIMARY KEY,
                            created_at TEXT NOT NULL,
                            metadata_json TEXT
                        )
                        """
                    )
                )
                self._ensure_trace_steps_schema(conn)
            return

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
        if self.engine:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS trace_steps (
                        id BIGSERIAL PRIMARY KEY,
                        trace_id TEXT NOT NULL,
                        step_type TEXT NOT NULL,
                        step_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
            )
            return

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
        if self.engine:
            with self.engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO traces (id, created_at, metadata_json) VALUES (:id, :created_at, :metadata_json)"),
                    {"id": trace_id, "created_at": created_at, "metadata_json": payload},
                )
        else:
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
        if self.engine:
            with self.engine.begin() as conn:
                self._ensure_trace_steps_schema(conn)
                conn.execute(
                    text(
                        """
                        INSERT INTO trace_steps (trace_id, step_type, step_json, created_at)
                        VALUES (:trace_id, :step_type, :step_json, :created_at)
                        """
                    ),
                    {
                        "trace_id": trace_id,
                        "step_type": step_type,
                        "step_json": json.dumps(payload),
                        "created_at": created_at,
                    },
                )
        else:
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

        self._emit_otel_span(trace_id, step_type, created_at, payload)

    def record_memory_write_decision(self, trace_id: str, **payload: Any) -> None:
        if not self.enabled or not trace_id:
            return
        self.record_step(trace_id, "memory_write_decision", payload)

    def _emit_otel_span(
        self,
        trace_id: str,
        step_type: str,
        created_at: str,
        payload: Dict[str, Any],
    ) -> None:
        if os.getenv("ORCH_OTEL_ENABLED", "0") != "1":
            return
        if otel_trace is None:
            return

        attributes: Dict[str, Any] = {
            "orchestrator.trace_id": trace_id,
            "trace.step_type": step_type,
            "trace.created_at": created_at,
        }

        for key in OTEL_TRACE_STEP_KEYS:
            if key in payload:
                value = payload.get(key)
                if isinstance(value, (str, int, float, bool)):
                    attributes[f"trace.{key}"] = value

        tracer = otel_trace.get_tracer("orchestrators_v2.trace_steps")
        with tracer.start_as_current_span(f"trace_step.{step_type}", attributes=attributes):
            return


_tracer: Optional[TraceStore] = None


def get_tracer() -> TraceStore:
    global _tracer
    if _tracer is None:
        _tracer = TraceStore()
    return _tracer
