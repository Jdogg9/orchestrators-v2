from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_HITL_DB = "instance/hitl_queue.db"


@dataclass(frozen=True)
class HitlRequest:
    request_id: str
    created_at: str
    status: str
    payload: Dict[str, Any]


class HitlQueue:
    def __init__(self, db_path: Optional[str] = None, enabled: bool = True) -> None:
        self.enabled = enabled and os.getenv("ORCH_INTENT_HITL_ENABLED", "1") == "1"
        self.db_path = db_path or os.getenv("ORCH_INTENT_HITL_DB_PATH", DEFAULT_HITL_DB)
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hitl_queue (
                    request_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def enqueue(self, payload: Dict[str, Any]) -> Optional[HitlRequest]:
        if not self.enabled:
            return None
        request_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO hitl_queue (request_id, created_at, status, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (request_id, created_at, "pending", json.dumps(payload, separators=(",", ":"))),
            )
            conn.commit()
        return HitlRequest(request_id=request_id, created_at=created_at, status="pending", payload=payload)