import hashlib
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import text

from src.db import get_engine
from src.tracer import get_tracer

DEFAULT_MEMORY_DB = "instance/orchestrator_core.db"

ALLOWED_DECISION_REASONS = {
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

SECRET_PATTERNS = [
    r"Bearer\s+[A-Za-z0-9_\-.]+",
    r"sk-[A-Za-z0-9_\-]{20,}",
    r"ghp_[A-Za-z0-9_\-]{20,}",
    r"-----BEGIN[\sA-Z]+PRIVATE KEY-----",
]

CONTROL_CHARS_PATTERN = r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+"
INTENT_PREFIXES = [
    r"remember this",
    r"remember that",
    r"don't forget",
    r"save this",
    r"store this",
    r"keep in mind",
    r"make a note",
]


def _env_flag(key: str, default: str = "0") -> bool:
    return os.getenv(key, default) == "1"


def _env_value(key: str, default: str) -> str:
    return os.getenv(key, default)


def _memory_db_path() -> str:
    return _env_value("ORCH_MEMORY_DB_PATH", DEFAULT_MEMORY_DB)


def _contains_secret_like(text: str) -> bool:
    if not text:
        return False
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def _redact_sensitive(text: str) -> str:
    if not text:
        return text
    scrubbed = text
    for pattern in SECRET_PATTERNS:
        scrubbed = re.sub(pattern, "[REDACTED]", scrubbed, flags=re.IGNORECASE)
    return scrubbed


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = re.sub(CONTROL_CHARS_PATTERN, " ", text)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _strip_intent_prefix(text: str) -> str:
    if not text:
        return ""
    lowered = text.lower()
    for prefix in INTENT_PREFIXES:
        match = re.match(rf"^\s*{prefix}\s*[:\-–—]?\s*", lowered)
        if match:
            return text[match.end():].strip()
    return text


def _scrub_candidate_text(text: str, write_policy: str) -> str:
    if not text:
        return ""

    candidate = _normalize_text(text)
    if write_policy == "strict":
        candidate = _strip_intent_prefix(candidate)
    candidate = _normalize_text(candidate)

    max_chars = int(_env_value("ORCH_MEMORY_MAX_CHARS", "500"))
    if max_chars > 0 and len(candidate) > max_chars:
        candidate = candidate[:max_chars].rstrip()

    return _redact_sensitive(candidate)


def should_capture_user_message(text: str, write_policy: str) -> bool:
    if write_policy == "off":
        return False
    if write_policy == "capture_only":
        return len(text.strip()) >= 20
    if write_policy == "strict":
        intent_keywords = [
            "remember this",
            "remember that",
            "don't forget",
            "save this",
            "store this",
            "keep in mind",
            "make a note",
        ]
        lower = text.lower()
        return any(keyword in lower for keyword in intent_keywords)
    return False


def _ensure_memory_candidates_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
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
        )
        """
    )


def _ensure_memory_candidates_schema_sql(conn) -> None:
    conn.execute(
        text(
            """
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
            )
            """
        )
    )


def _record_memory_write_decision(trace_id: Optional[str], **payload: Any) -> None:
    reason = payload.get("reason")
    if reason and reason not in ALLOWED_DECISION_REASONS:
        payload["reason"] = "deny:error"
        payload["original_reason"] = reason
    tracer = get_tracer()
    if trace_id:
        tracer.record_memory_write_decision(trace_id, **payload)


def capture_candidate_memory(
    user_id_hash: str,
    conversation_id: Optional[str],
    text: str,
    scope: str = "global",
    source: str = "chat",
    trace_id: Optional[str] = None,
) -> Optional[str]:
    if not _env_flag("ORCH_MEMORY_ENABLED", "0"):
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:feature_disabled",
            explicit_intent=True,
            write_policy=_env_value("ORCH_MEMORY_WRITE_POLICY", "off"),
            scrub_applied=False,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None

    if not _env_flag("ORCH_MEMORY_CAPTURE_ENABLED", "0"):
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:feature_disabled",
            explicit_intent=True,
            write_policy=_env_value("ORCH_MEMORY_WRITE_POLICY", "off"),
            scrub_applied=False,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None

    write_policy = _env_value("ORCH_MEMORY_WRITE_POLICY", "off")
    if write_policy not in ("strict", "capture_only"):
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:policy_write_disabled",
            explicit_intent=True,
            write_policy=write_policy,
            scrub_applied=False,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None

    raw_text = text or ""
    if _contains_secret_like(raw_text):
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:sensitive_content",
            explicit_intent=True,
            write_policy=write_policy,
            scrub_applied=False,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None

    scrubbed = _scrub_candidate_text(raw_text, write_policy)
    if not scrubbed or len(scrubbed.strip()) < 10:
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:scrubbed_too_short",
            explicit_intent=True,
            write_policy=write_policy,
            scrub_applied=True,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None

    if _contains_secret_like(scrubbed):
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:sensitive_content",
            explicit_intent=True,
            write_policy=write_policy,
            scrub_applied=True,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None

    content_hash = hashlib.sha256(scrubbed.encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")))

    engine = get_engine()
    if engine:
        return _capture_candidate_memory_sql(
            engine=engine,
            user_id_hash=user_id_hash,
            conversation_id=conversation_id,
            scope=scope,
            source=source,
            scrubbed=scrubbed,
            content_hash=content_hash,
            now=now,
            expires_at=expires_at,
            write_policy=write_policy,
            trace_id=trace_id,
        )

    memory_db = _memory_db_path()
    Path(memory_db).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(memory_db)
    try:
        _ensure_memory_candidates_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, passes FROM memory_candidates
            WHERE user_id_hash = ? AND scope = ? AND content_hash = ?
            AND datetime(last_seen_at) > datetime('now', '-24 hours')
            LIMIT 1
            """,
            (user_id_hash, scope, content_hash),
        )
        existing = cursor.fetchone()
        if existing:
            candidate_id, passes = existing
            cursor.execute(
                """
                UPDATE memory_candidates
                SET last_seen_at = ?, passes = ?, expires_at = ?
                WHERE id = ?
                """,
                (now.isoformat(), passes + 1, expires_at.isoformat(), candidate_id),
            )
            conn.commit()
            _record_memory_write_decision(
                trace_id,
                decision="allow",
                reason="allow:dedupe_update",
                explicit_intent=True,
                write_policy=write_policy,
                scrub_applied=True,
                ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
                scope=scope,
                source=source,
                candidate_id_hash=hashlib.sha256(candidate_id.encode()).hexdigest()[:12],
            )
            return candidate_id

        candidate_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO memory_candidates (
                id, user_id_hash, conversation_id, scope, content, content_hash,
                created_at, last_seen_at, ttl_minutes, expires_at, source, passes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                user_id_hash,
                conversation_id,
                scope,
                scrubbed,
                content_hash,
                now.isoformat(),
                now.isoformat(),
                int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
                expires_at.isoformat(),
                source,
                1,
            ),
        )
        conn.commit()
        _record_memory_write_decision(
            trace_id,
            decision="allow",
            reason="allow:explicit_intent" if write_policy == "strict" else "allow:capture_only",
            explicit_intent=True,
            write_policy=write_policy,
            scrub_applied=True,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
            candidate_id_hash=hashlib.sha256(candidate_id.encode()).hexdigest()[:12],
        )
        return candidate_id
    except Exception:
        conn.rollback()
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:error",
            explicit_intent=True,
            write_policy=write_policy,
            scrub_applied=True,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None
    finally:
        conn.close()


def _capture_candidate_memory_sql(
    *,
    engine,
    user_id_hash: str,
    conversation_id: Optional[str],
    scope: str,
    source: str,
    scrubbed: str,
    content_hash: str,
    now: datetime,
    expires_at: datetime,
    write_policy: str,
    trace_id: Optional[str],
) -> Optional[str]:
    cutoff = now - timedelta(hours=24)
    try:
        with engine.begin() as conn:
            _ensure_memory_candidates_schema_sql(conn)
            existing = conn.execute(
                text(
                    """
                    SELECT id, passes FROM memory_candidates
                    WHERE user_id_hash = :user_id_hash
                      AND scope = :scope
                      AND content_hash = :content_hash
                      AND last_seen_at > :cutoff
                    LIMIT 1
                    """
                ),
                {
                    "user_id_hash": user_id_hash,
                    "scope": scope,
                    "content_hash": content_hash,
                    "cutoff": cutoff.isoformat(),
                },
            ).fetchone()

            if existing:
                candidate_id, passes = existing
                conn.execute(
                    text(
                        """
                        UPDATE memory_candidates
                        SET last_seen_at = :last_seen_at,
                            passes = :passes,
                            expires_at = :expires_at
                        WHERE id = :candidate_id
                        """
                    ),
                    {
                        "last_seen_at": now.isoformat(),
                        "passes": (passes or 0) + 1,
                        "expires_at": expires_at.isoformat(),
                        "candidate_id": candidate_id,
                    },
                )
                _record_memory_write_decision(
                    trace_id,
                    decision="allow",
                    reason="allow:dedupe_update",
                    explicit_intent=True,
                    write_policy=write_policy,
                    scrub_applied=True,
                    ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
                    scope=scope,
                    source=source,
                    candidate_id_hash=hashlib.sha256(candidate_id.encode()).hexdigest()[:12],
                )
                return candidate_id

            candidate_id = str(uuid.uuid4())
            conn.execute(
                text(
                    """
                    INSERT INTO memory_candidates (
                        id, user_id_hash, conversation_id, scope, content, content_hash,
                        created_at, last_seen_at, ttl_minutes, expires_at, source, passes
                    ) VALUES (
                        :id, :user_id_hash, :conversation_id, :scope, :content, :content_hash,
                        :created_at, :last_seen_at, :ttl_minutes, :expires_at, :source, :passes
                    )
                    """
                ),
                {
                    "id": candidate_id,
                    "user_id_hash": user_id_hash,
                    "conversation_id": conversation_id,
                    "scope": scope,
                    "content": scrubbed,
                    "content_hash": content_hash,
                    "created_at": now.isoformat(),
                    "last_seen_at": now.isoformat(),
                    "ttl_minutes": int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
                    "expires_at": expires_at.isoformat(),
                    "source": source,
                    "passes": 1,
                },
            )
            _record_memory_write_decision(
                trace_id,
                decision="allow",
                reason="allow:explicit_intent" if write_policy == "strict" else "allow:capture_only",
                explicit_intent=True,
                write_policy=write_policy,
                scrub_applied=True,
                ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
                scope=scope,
                source=source,
                candidate_id_hash=hashlib.sha256(candidate_id.encode()).hexdigest()[:12],
            )
            return candidate_id
    except Exception:
        _record_memory_write_decision(
            trace_id,
            decision="deny",
            reason="deny:error",
            explicit_intent=True,
            write_policy=write_policy,
            scrub_applied=True,
            ttl_minutes=int(_env_value("ORCH_MEMORY_CAPTURE_TTL_MINUTES", "180")),
            scope=scope,
            source=source,
        )
        return None
