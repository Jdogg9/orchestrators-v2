from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import text

from src.db import get_engine

DEFAULT_TRACE_DB = os.getenv("ORCH_TRACE_DB_PATH", "instance/trace.db")

SENSITIVE_KEYS = {
    "authorization",
    "auth",
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "cookie",
    "set-cookie",
    "access_token",
    "refresh_token",
    "email",
}

TOKEN_PATTERNS = [
    r"Bearer\s+[A-Za-z0-9_\-\.]+",
    r"sk-[A-Za-z0-9_\-]{20,}",
    r"ghp_[A-Za-z0-9_\-]{36,}",
    r"gho_[A-Za-z0-9_\-]{36,}",
    r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
    r"AIza[A-Za-z0-9_\-]{35}",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
]

TOKEN_REGEX = re.compile("|".join(TOKEN_PATTERNS), re.IGNORECASE)


def trust_panel_enabled() -> bool:
    return os.getenv("ORCH_TRUST_PANEL_ENABLED", "0") == "1"


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    if os.getenv("ORCH_SQLITE_WAL_ENABLED", "1") == "1":
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_limit(limit: Optional[int], default: int = 50, maximum: int = 200) -> int:
    value = limit if isinstance(limit, int) else default
    value = max(1, value)
    return min(value, maximum)


def _sanitize_str(value: str) -> Tuple[str, int]:
    redactions = 0
    if TOKEN_REGEX.search(value):
        redactions += 1
        value = TOKEN_REGEX.sub("<redacted>", value)

    max_len = int(os.getenv("ORCH_TRUST_PANEL_MAX_VALUE_CHARS", "500"))
    if max_len > 0 and len(value) > max_len:
        redactions += 1
        value = value[: max_len - 12] + "...<truncated>"
    return value, redactions


def _sanitize_value(key: Optional[str], value: Any) -> Tuple[Any, int]:
    redactions = 0
    key_lower = key.lower() if isinstance(key, str) else ""
    if key_lower in SENSITIVE_KEYS:
        return "<redacted>", 1

    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in value.items():
            clean, hits = _sanitize_value(str(k), v)
            sanitized[str(k)] = clean
            redactions += hits
        return sanitized, redactions

    if isinstance(value, list):
        sanitized_list: List[Any] = []
        for item in value:
            clean, hits = _sanitize_value(None, item)
            sanitized_list.append(clean)
            redactions += hits
        return sanitized_list, redactions

    if isinstance(value, str):
        clean, hits = _sanitize_str(value)
        redactions += hits
        return clean, redactions

    return value, redactions


def sanitize_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    sanitized, redactions = _sanitize_value(None, payload)
    if not isinstance(sanitized, dict):
        return {"value": sanitized}, redactions
    return sanitized, redactions


def _hash_event(step_type: str, created_at: str, payload: Dict[str, Any]) -> str:
    packed = json.dumps(
        {
            "step_type": step_type,
            "created_at": created_at,
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(packed).hexdigest()


def _chain_hash(prev_hash: str, event_hash: str) -> str:
    return hashlib.sha256(f"{prev_hash}{event_hash}".encode("utf-8")).hexdigest()


def list_trust_events(
    limit: Optional[int] = None,
    step_types: Optional[Iterable[str]] = None,
    trace_id: Optional[str] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    db_path = os.getenv("ORCH_TRACE_DB_PATH", DEFAULT_TRACE_DB)
    max_events = int(os.getenv("ORCH_TRUST_PANEL_MAX_EVENTS", "200"))
    limit_value = _normalize_limit(limit, maximum=max_events)
    step_types_list = [s for s in (step_types or []) if s]

    if not Path(db_path).exists() and not get_engine():
        return {"events": [], "count": 0, "limit": limit_value, "truncated": False}

    rows = []
    engine = get_engine()
    if engine:
        conditions = []
        params: Dict[str, Any] = {"limit": limit_value}
        if trace_id:
            conditions.append("trace_id = :trace_id")
            params["trace_id"] = trace_id
        if step_types_list:
            placeholders = ",".join([f":step_{idx}" for idx in range(len(step_types_list))])
            conditions.append(f"step_type IN ({placeholders})")
            params.update({f"step_{idx}": step for idx, step in enumerate(step_types_list)})
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = text(
            f"""
            SELECT trace_id, step_type, step_json, created_at
            FROM trace_steps
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )
        with engine.begin() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
    else:
        with _get_conn(db_path) as conn:
            params_list: List[Any] = []
            conditions = []
            if trace_id:
                conditions.append("trace_id = ?")
                params_list.append(trace_id)
            if step_types_list:
                placeholders = ",".join(["?"] * len(step_types_list))
                conditions.append(f"step_type IN ({placeholders})")
                params_list.extend(step_types_list)
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = (
                "SELECT trace_id, step_type, step_json, created_at "
                "FROM trace_steps "
                f"{where_clause} "
                "ORDER BY created_at DESC "
                "LIMIT ?"
            )
            params_list.append(limit_value)
            cursor = conn.execute(query, params_list)
            rows = cursor.fetchall()

    events = []
    for row in rows:
        step_json = row[2]
        try:
            payload = json.loads(step_json) if step_json else {}
        except json.JSONDecodeError:
            payload = {}
        sanitized_payload, redactions = sanitize_payload(payload)
        event_hash = _hash_event(row[1], row[3], sanitized_payload)
        event = {
            "trace_id": row[0],
            "step_type": row[1],
            "created_at": row[3],
            "payload": sanitized_payload,
            "event_hash": event_hash,
            "redactions": redactions,
        }
        if debug and os.getenv("ORCH_TRUST_PANEL_DEBUG", "0") == "1":
            event["payload_size"] = len(step_json) if step_json else 0
        events.append(event)

    return {
        "events": events,
        "count": len(events),
        "limit": limit_value,
        "truncated": len(events) >= limit_value,
    }


def get_trace_report(trace_id: str, debug: bool = False) -> Dict[str, Any]:
    if not trace_id:
        return {"error": "trace_id_required"}

    db_path = os.getenv("ORCH_TRACE_DB_PATH", DEFAULT_TRACE_DB)
    engine = get_engine()
    metadata = {}

    if engine:
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT metadata_json, created_at FROM traces WHERE id = :trace_id"),
                {"trace_id": trace_id},
            ).fetchone()
            if result:
                metadata_json = result[0]
                try:
                    metadata = json.loads(metadata_json) if metadata_json else {}
                except json.JSONDecodeError:
                    metadata = {}
                metadata.setdefault("created_at", result[1])
    else:
        if Path(db_path).exists():
            with _get_conn(db_path) as conn:
                row = conn.execute(
                    "SELECT metadata_json, created_at FROM traces WHERE id = ?",
                    (trace_id,),
                ).fetchone()
                if row:
                    metadata_json = row[0]
                    try:
                        metadata = json.loads(metadata_json) if metadata_json else {}
                    except json.JSONDecodeError:
                        metadata = {}
                    metadata.setdefault("created_at", row[1])

    max_steps = int(os.getenv("ORCH_TRUST_PANEL_MAX_EVENTS", "200"))
    steps_response = list_trust_events(trace_id=trace_id, limit=max_steps, debug=debug)
    steps = steps_response.get("events", [])
    chain = "0" * 64
    for step in steps[::-1]:
        chain = _chain_hash(chain, step["event_hash"])
        step["chain_hash"] = chain

    sanitized_metadata, redactions = sanitize_payload(metadata if isinstance(metadata, dict) else {})
    response = {
        "trace_id": trace_id,
        "metadata": sanitized_metadata,
        "metadata_redactions": redactions,
        "steps": list(reversed(steps)),
        "step_count": len(steps),
        "steps_truncated": steps_response.get("truncated", False),
        "chain_hash": chain,
    }
    if debug and os.getenv("ORCH_TRUST_PANEL_DEBUG", "0") == "1":
        response["metadata_size"] = len(json.dumps(metadata)) if metadata else 0
    return response


def verify_trace_chain(trace_id: str, expected_hash: Optional[str] = None) -> Dict[str, Any]:
    report = get_trace_report(trace_id, debug=False)
    if "error" in report:
        return report

    chain_hash = report.get("chain_hash")
    verified = True
    reason = "computed"
    if expected_hash:
        verified = expected_hash == chain_hash
        reason = "match" if verified else "mismatch"

    return {
        "trace_id": trace_id,
        "verified": verified,
        "reason": reason,
        "chain_hash": chain_hash,
        "step_count": report.get("step_count", 0),
    }
