#!/usr/bin/env bash
set -euo pipefail

STRICT_MODE="${ORCH_SECURITY_STRICT:-0}"

ensure_tool() {
  local tool="$1"
  local optional="${2:-0}"
  if ! command -v "$tool" >/dev/null 2>&1; then
    if [ "$STRICT_MODE" = "1" ] && [ "$optional" != "1" ]; then
      echo "ERROR: required tool '$tool' not found" >&2
      exit 1
    fi
    echo "WARN: '$tool' not found; skipping" >&2
    return 1
  fi
  return 0
}

echo "==> Security scan (SAST + dependency audit)"

if ensure_tool bandit; then
  echo "--> bandit"
  bandit -r src -c .bandit
fi

if ensure_tool semgrep 1; then
  echo "--> semgrep"
  semgrep --config=auto src
fi

if ensure_tool pip-audit; then
  echo "--> pip-audit"
  pip-audit -r requirements.txt
fi

if ensure_tool trivy 1; then
  echo "--> trivy"
  trivy fs --scanners vuln,secret --severity HIGH,CRITICAL --exit-code 1 .
fi

echo "OK: security scan complete"
