#!/usr/bin/env python3
"""Generate a PDF compliance report from trace receipts (if present)."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _fetch_trace_summary(db_path: Path) -> Tuple[int, int, List[Tuple[str, str]]]:
    if not db_path.exists():
        return 0, 0, []

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM traces")
        trace_count = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM trace_steps")
        step_count = cursor.fetchone()[0] or 0
        cursor.execute(
            "SELECT id, created_at FROM traces ORDER BY created_at DESC LIMIT 5"
        )
        recent = [(row[0], row[1]) for row in cursor.fetchall()]
        return trace_count, step_count, recent
    finally:
        conn.close()


def generate_report(output_path: Path, trace_db_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    trace_count, step_count, recent_traces = _fetch_trace_summary(trace_db_path)

    now = datetime.now(timezone.utc).isoformat()
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    y = height - inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, y, "ORCHESTRATORS_V2 Compliance Report")

    y -= 0.4 * inch
    c.setFont("Helvetica", 11)
    c.drawString(inch, y, f"Generated: {now}")

    y -= 0.3 * inch
    c.drawString(inch, y, f"Trace DB: {trace_db_path}")

    y -= 0.4 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch, y, "Trace Receipts Summary")

    y -= 0.3 * inch
    c.setFont("Helvetica", 11)
    c.drawString(inch, y, f"Total traces: {trace_count}")

    y -= 0.25 * inch
    c.drawString(inch, y, f"Total trace steps: {step_count}")

    y -= 0.4 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch, y, "Most Recent Traces")

    y -= 0.25 * inch
    c.setFont("Helvetica", 10)
    if not recent_traces:
        c.drawString(inch, y, "No trace receipts found. (Expected in CI or pre-prod runs)")
    else:
        for trace_id, created_at in recent_traces:
            if y < inch:
                c.showPage()
                y = height - inch
                c.setFont("Helvetica", 10)
            c.drawString(inch, y, f"{created_at} — {trace_id}")
            y -= 0.2 * inch

    y -= 0.3 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch, y, "Token Telemetry")

    y -= 0.25 * inch
    c.setFont("Helvetica", 10)
    c.drawString(
        inch,
        y,
        "Token usage receipts (input/output/utilization) are recorded per request when tracing is enabled.",
    )

    c.showPage()
    c.save()


def generate_jsonld(output_path: Path, trace_db_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trace_count, step_count, recent_traces = _fetch_trace_summary(trace_db_path)
    now = datetime.now(timezone.utc).isoformat()

    payload = {
        "@context": {
            "@vocab": "https://nist.gov/ai/rmf/1.0#",
            "schema": "https://schema.org/",
        },
        "@type": "schema:Dataset",
        "schema:name": "ORCHESTRATORS_V2 Governance Metrics",
        "schema:dateCreated": now,
        "schema:description": "Machine-readable governance export for NIST AI RMF Measure and Govern functions.",
        "govern": {
            "function": "Govern",
            "artifact": "trace_receipts",
            "trace_db": str(trace_db_path),
            "trace_count": trace_count,
        },
        "measure": {
            "function": "Measure",
            "subcategories": [
                {
                    "id": "Measure-2.1",
                    "description": "Token utilization monitoring and capacity bounds evidence.",
                    "evidence": [
                        "orch.token.utilization_ratio",
                        "orch.token.pruned_input_tokens",
                        "orch.token.pruned_messages",
                        "orch.token.pruned_turns",
                    ],
                }
            ],
            "trace_steps_total": step_count,
            "recent_traces": [
                {"trace_id": trace_id, "created_at": created_at}
                for trace_id, created_at in recent_traces
            ],
        },
    }
    output_path.write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    trace_db = Path(os.getenv("ORCH_TRACE_DB_PATH", repo_root / "instance" / "trace.db"))
    output = Path(os.getenv("COMPLIANCE_REPORT_PATH", repo_root / "reports" / "compliance_report.pdf"))
    jsonld_output = Path(
        os.getenv("COMPLIANCE_REPORT_JSONLD_PATH", repo_root / "reports" / "compliance_report.jsonld")
    )
    generate_report(output, trace_db)
    generate_jsonld(jsonld_output, trace_db)
    print(f"Compliance report generated: {output}")
    print(f"Compliance report JSON-LD generated: {jsonld_output}")
