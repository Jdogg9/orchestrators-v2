#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_boundary_check(repo_root: Path) -> None:
    script_path = repo_root / "scripts" / "verify_public_boundary.sh"
    completed = subprocess.run(
        ["bash", str(script_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        raise RuntimeError("Boundary verification failed. See output above.")
    print("PASS: boundary verified")


def _demo_flow(receipt_dir: Path) -> Path:
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from src.orchestrator import Orchestrator
    from src.tracer import TraceStore

    os.environ.setdefault("ORCH_LLM_ENABLED", "0")
    os.environ.setdefault("ORCH_TOOL_WEB_SEARCH_ENABLED", "0")
    os.environ.setdefault("ORCH_TRACE_ENABLED", "1")

    trace_db_path = receipt_dir / "trace.db"
    os.environ["ORCH_TRACE_DB_PATH"] = str(trace_db_path)

    tracer = TraceStore(db_path=str(trace_db_path), enabled=True)
    handle = tracer.start_trace({
        "route": "demo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    orchestrator = Orchestrator()
    messages = [{"role": "user", "content": "calc 2 + 2"}]
    result = orchestrator.handle(messages)

    if handle:
        tracer.record_step(
            handle.trace_id,
            "demo_step",
            {
                "assistant_content": result["assistant_content"],
                "route_decision": getattr(result.get("route_decision"), "__dict__", None),
            },
        )

    receipt_path = receipt_dir / "demo_receipt.json"
    receipt_payload = {
        "trace_id": handle.trace_id if handle else None,
        "trace_db": str(trace_db_path),
        "assistant_content": result["assistant_content"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path.write_text(json.dumps(receipt_payload, indent=2))

    print(f"RECEIPT_PATH={receipt_path}")
    print(f"TRACE_DB_PATH={trace_db_path}")
    return receipt_path


def _simulate_exfiltration_block() -> None:
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from src.tool_registry import ToolRegistry, ToolSpec

    os.environ["ORCH_TOOL_POLICY_ENFORCE"] = "1"
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="python_exec",
            description="unsafe exec",
            handler=lambda code: code,
            safe=False,
            requires_sandbox=True,
        )
    )
    result = registry.execute("python_exec", code="curl https://example.com")
    if result.get("status") == "error" and str(result.get("error", "")).startswith("policy_denied"):
        print("PASS: simulated exfiltration attempt blocked")
        return
    raise RuntimeError("Simulated exfiltration was not blocked as expected.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Killer demo: local receipts + boundary verification")
    parser.add_argument("--skip-boundary", action="store_true", help="Skip boundary verification script")
    parser.add_argument("--skip-exfiltration", action="store_true", help="Skip exfiltration demo")
    args = parser.parse_args()

    repo_root = _repo_root()
    receipt_dir = Path(tempfile.mkdtemp(prefix="orch_receipts_"))
    _demo_flow(receipt_dir)

    if not args.skip_exfiltration:
        _simulate_exfiltration_block()

    if not args.skip_boundary:
        _run_boundary_check(repo_root)

    print("PASS: demo complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
