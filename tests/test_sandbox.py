import json
import subprocess
import sys
from pathlib import Path


def _run_python_exec(payload: dict) -> tuple[int, dict]:
    script_path = Path(__file__).resolve().parents[1] / "sandbox_tools" / "python_exec.py"
    process = subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = process.stdout.strip() or "{}"
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = {"status": "error", "error": "invalid_json", "raw": stdout}
    return process.returncode, data


def test_python_exec_success():
    code = "print('hello')"
    exit_code, data = _run_python_exec({"code": code})

    assert exit_code == 0
    assert data["status"] == "ok"
    assert data["stdout"] == "hello"


def test_python_exec_missing_code():
    exit_code, data = _run_python_exec({})

    assert exit_code != 0
    assert data["status"] == "error"
    assert data["error"] == "missing_code"


def test_python_exec_error_exit():
    code = "import sys\nsys.exit(2)"
    exit_code, data = _run_python_exec({"code": code})

    assert exit_code == 2
    assert data["status"] == "error"
    assert data["error"]
    assert data["exit_code"] == 2
