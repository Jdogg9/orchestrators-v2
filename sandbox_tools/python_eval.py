import json
import sys


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    expression = payload.get("expression", "")
    if not expression:
        print(json.dumps({"status": "error", "error": "missing_expression"}))
        return 1
    try:
        result = eval(expression, {"__builtins__": {}})
        print(json.dumps({"status": "ok", "result": result}))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
