#!/usr/bin/env python3
"""Migrate SQLite trace + memory data into Postgres."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

from sqlalchemy import text
from src.db import get_engine

TRACE_INSERT = """
INSERT INTO traces (id, created_at, metadata_json)
VALUES (:id, :created_at, :metadata_json)
ON CONFLICT (id) DO NOTHING
"""

TRACE_STEP_INSERT = """
INSERT INTO trace_steps (trace_id, step_type, step_json, created_at)
VALUES (:trace_id, :step_type, :step_json, :created_at)
"""

MEMORY_INSERT = """
INSERT INTO memory_candidates (
  id, user_id_hash, conversation_id, scope, content, content_hash,
  created_at, last_seen_at, ttl_minutes, expires_at, source, passes
)
VALUES (
  :id, :user_id_hash, :conversation_id, :scope, :content, :content_hash,
  :created_at, :last_seen_at, :ttl_minutes, :expires_at, :source, :passes
)
ON CONFLICT (id) DO NOTHING
"""


def _rows(conn: sqlite3.Connection, sql: str) -> Iterable[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(sql)
    for row in cursor.fetchall():
        yield row


def main() -> int:
    db_url = os.getenv("ORCH_DATABASE_URL")
    if not db_url:
        raise SystemExit("ORCH_DATABASE_URL is required")

    trace_db = Path(os.getenv("ORCH_TRACE_DB_PATH", "instance/trace.db"))
    memory_db = Path(os.getenv("ORCH_MEMORY_DB_PATH", "instance/orchestrator_core.db"))

    engine = get_engine()
    if not engine:
        raise SystemExit("Failed to create database engine")

    migrated_traces = 0
    migrated_steps = 0
    migrated_memory = 0

    if trace_db.exists():
        with sqlite3.connect(trace_db) as conn:
            traces = list(_rows(conn, "SELECT id, created_at, metadata_json FROM traces"))
            steps = list(_rows(conn, "SELECT trace_id, step_type, step_json, created_at FROM trace_steps"))
        with engine.begin() as pg:
            for row in traces:
                pg.execute(text(TRACE_INSERT), dict(row))
                migrated_traces += 1
            for row in steps:
                pg.execute(text(TRACE_STEP_INSERT), dict(row))
                migrated_steps += 1

    if memory_db.exists():
        with sqlite3.connect(memory_db) as conn:
            memory_rows = list(_rows(conn, """
                SELECT id, user_id_hash, conversation_id, scope, content, content_hash,
                       created_at, last_seen_at, ttl_minutes, expires_at, source, passes
                FROM memory_candidates
            """))
        with engine.begin() as pg:
            for row in memory_rows:
                pg.execute(text(MEMORY_INSERT), dict(row))
                migrated_memory += 1

    print(
        "Migrated SQLite -> Postgres: "
        f"traces={migrated_traces}, steps={migrated_steps}, memory_candidates={migrated_memory}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
