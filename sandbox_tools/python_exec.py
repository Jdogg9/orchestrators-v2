import json
import os
import subprocess
import sys
import tempfile


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    code = payload.get("code", "")
    stdin = payload.get("stdin", "")
    if not code:
        print(json.dumps({"status": "error", "error": "missing_code"}))
        return 1

    script_path = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", prefix="sandbox_", encoding="utf-8") as handle:
            handle.write(code)
            script_path = handle.name
    except OSError as exc:
        print(json.dumps({"status": "error", "error": f"write_failed:{exc}"}))
        return 1

    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", script_path],
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
            cwd="/tmp",
            env={"PYTHONUNBUFFERED": "1"},
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1
    finally:
        if script_path:
            try:
                os.remove(script_path)
            except OSError:
                pass

    if completed.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": completed.stderr.strip() or "script_failed",
                    "exit_code": completed.returncode,
                }
            )
        )
        return completed.returncode

    print(
        json.dumps(
            {
                "status": "ok",
                "stdout": completed.stdout.strip(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
