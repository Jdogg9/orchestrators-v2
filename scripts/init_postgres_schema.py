#!/usr/bin/env python3
"""Initialize Postgres schema for traces and memory candidates."""
from __future__ import annotations

import os
from sqlalchemy import text
from src.db import get_engine

TRACE_SQL = """
CREATE TABLE IF NOT EXISTS traces (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  metadata_json TEXT
);
"""

TRACE_STEPS_SQL = """
CREATE TABLE IF NOT EXISTS trace_steps (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  step_type TEXT NOT NULL,
  step_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""

MEMORY_SQL = """
CREATE TABLE IF NOT EXISTS memory_candidates (
  id TEXT PRIMARY KEY,
  user_id_hash TEXT NOT NULL,
  conversation_id TEXT,
  scope TEXT NOT NULL,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  ttl_minutes INTEGER NOT NULL,
  expires_at TEXT NOT NULL,
  source TEXT,
  passes INTEGER DEFAULT 0
);
"""


def main() -> int:
    if not os.getenv("ORCH_DATABASE_URL"):
        raise SystemExit("ORCH_DATABASE_URL is required to initialize Postgres schema")

    engine = get_engine()
    if not engine:
        raise SystemExit("Failed to create database engine")

    with engine.begin() as conn:
        conn.execute(text(TRACE_SQL))
        conn.execute(text(TRACE_STEPS_SQL))
        conn.execute(text(MEMORY_SQL))

    print("Postgres schema initialized: traces, trace_steps, memory_candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
