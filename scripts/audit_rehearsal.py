#!/usr/bin/env python3
"""Governance dry-run: simulate a Tier 3 trace and generate compliance reports.

Creates a synthetic trace DB with high-token telemetry (no LLM calls), then
runs the compliance report generator to produce PDF + JSON-LD evidence.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_compliance_report import generate_report, generate_jsonld


def _init_trace_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                metadata_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trace_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                step_type TEXT NOT NULL,
                step_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _insert_trace(db_path: Path, trace_id: str, metadata: Dict[str, Any]) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(metadata)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM traces WHERE id = ?", (trace_id,))
        conn.execute(
            "INSERT INTO traces (id, created_at, metadata_json) VALUES (?, ?, ?)",
            (trace_id, created_at, payload),
        )
        conn.commit()


def _insert_steps(db_path: Path, trace_id: str, steps: List[Dict[str, Any]]) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM trace_steps WHERE trace_id = ?", (trace_id,))
        for step in steps:
            created_at = step.get("created_at") or datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO trace_steps (trace_id, step_type, step_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (trace_id, step["step_type"], json.dumps(step["payload"]), created_at),
            )
        conn.commit()


def _build_rehearsal_steps(total_tokens: int, step_count: int) -> List[Dict[str, Any]]:
    per_step = max(1, total_tokens // step_count)
    steps = []
    for idx in range(step_count):
        steps.append(
            {
                "step_type": "audit_rehearsal",
                "payload": {
                    "step": idx + 1,
                    "tier": "tier3",
                    "tokens_used": per_step,
                    "note": "synthetic high-token rehearsal (no LLM invocation)",
                },
            }
        )
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an audit rehearsal dry-run.")
    repo_root = REPO_ROOT
    parser.add_argument(
        "--trace-db",
        default=str(repo_root / "instance" / "audit_rehearsal_trace.MOCK.db"),
        help="Path to synthetic trace DB (default: instance/audit_rehearsal_trace.MOCK.db)",
    )
    parser.add_argument(
        "--output-pdf",
        default=str(repo_root / "reports" / "compliance_report.pdf"),
        help="PDF output path",
    )
    parser.add_argument(
        "--output-jsonld",
        default=str(repo_root / "reports" / "compliance_report.jsonld"),
        help="JSON-LD output path",
    )
    parser.add_argument(
        "--total-tokens",
        type=int,
        default=120000,
        help="Synthetic token load to simulate Tier 3 stress",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=6,
        help="Number of synthetic trace steps",
    )

    args = parser.parse_args()

    trace_db = Path(args.trace_db)
    output_pdf = Path(args.output_pdf)
    output_jsonld = Path(args.output_jsonld)

    _init_trace_db(trace_db)

    trace_id = "audit-rehearsal-tier3"
    metadata = {
        "mode": "audit_rehearsal",
        "tier": "tier3",
        "total_tokens": args.total_tokens,
        "note": "synthetic stress run (no LLM calls)",
    }
    _insert_trace(trace_db, trace_id, metadata)

    steps = _build_rehearsal_steps(args.total_tokens, args.steps)
    _insert_steps(trace_db, trace_id, steps)

    generate_report(output_pdf, trace_db)
    generate_jsonld(output_jsonld, trace_db)

    print("Audit rehearsal complete.")
    print(f"Trace DB: {trace_db}")
    print(f"PDF: {output_pdf}")
    print(f"JSON-LD: {output_jsonld}")
    print("No LLM tokens were consumed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
