from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CACHE_DB = "instance/intent_cache.db"


@dataclass(frozen=True)
class IntentCacheEntry:
    policy_hash: str
    signature: str
    decision_json: Dict[str, Any]
    created_at: str
    expires_at: str
    stable: bool


class IntentCache:
    def __init__(self, db_path: Optional[str] = None, ttl_sec: Optional[int] = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self.db_path = db_path or os.getenv("ORCH_INTENT_CACHE_DB_PATH", DEFAULT_CACHE_DB)
        self.ttl_sec = ttl_sec or int(os.getenv("ORCH_INTENT_CACHE_TTL_SEC", "600"))
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS intent_cache (
                    policy_hash TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    stable INTEGER NOT NULL,
                    PRIMARY KEY (policy_hash, signature)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_intent_cache_expires
                ON intent_cache (expires_at)
                """
            )
            conn.commit()

    def get(self, policy_hash: str, signature: str) -> Optional[IntentCacheEntry]:
        if not self.enabled:
            return None
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT policy_hash, signature, decision_json, created_at, expires_at, stable
                FROM intent_cache
                WHERE policy_hash = ? AND signature = ? AND expires_at > ?
                """,
                (policy_hash, signature, now),
            ).fetchone()
            if not row:
                return None
            return IntentCacheEntry(
                policy_hash=row["policy_hash"],
                signature=row["signature"],
                decision_json=json.loads(row["decision_json"]),
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                stable=bool(row["stable"]),
            )

    def set(self, policy_hash: str, signature: str, decision: Dict[str, Any], stable: bool) -> None:
        if not self.enabled:
            return
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(seconds=max(self.ttl_sec, 1))
        payload = json.dumps(decision, separators=(",", ":"))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO intent_cache
                    (policy_hash, signature, decision_json, created_at, expires_at, stable)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    policy_hash,
                    signature,
                    payload,
                    created_at.isoformat(),
                    expires_at.isoformat(),
                    1 if stable else 0,
                ),
            )
            conn.commit()

    def invalidate_policy(self, policy_hash: str) -> None:
        if not self.enabled:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM intent_cache WHERE policy_hash = ?",
                (policy_hash,),
            )
            conn.commit()

    def prune_expired(self) -> int:
        if not self.enabled:
            return 0
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM intent_cache WHERE expires_at <= ?",
                (now,),
            )
            conn.commit()
            return cursor.rowcount