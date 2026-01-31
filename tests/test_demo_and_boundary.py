import json
import os
import subprocess
from pathlib import Path


def test_boundary_verification_script_runs():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "verify_public_boundary.sh"

    completed = subprocess.run(
        ["bash", str(script_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "PUBLIC BOUNDARY SAFE" in completed.stdout


def test_killer_demo_runs_offline_and_creates_receipt():
    repo_root = Path(__file__).resolve().parents[1]
    demo_path = repo_root / "examples" / "killer_demo_local_receipts" / "run_demo.py"

    env = dict(os.environ)
    env["ORCH_LLM_ENABLED"] = "0"
    env["ORCH_TOOL_WEB_SEARCH_ENABLED"] = "0"

    completed = subprocess.run(
        ["python", str(demo_path), "--skip-boundary"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "PASS: demo complete" in completed.stdout

    receipt_line = next(
        (line for line in completed.stdout.splitlines() if line.startswith("RECEIPT_PATH=")),
        None,
    )
    assert receipt_line, completed.stdout

    receipt_path = Path(receipt_line.split("=", 1)[1].strip())
    assert receipt_path.exists()
    payload = json.loads(receipt_path.read_text())
    assert "assistant_content" in payload
