#!/usr/bin/env bash
set -euo pipefail

if [ "${ORCH_DYNAMIC_SCAN_ENABLED:-0}" != "1" ]; then
  echo "Dynamic scan disabled (ORCH_DYNAMIC_SCAN_ENABLED!=1)"
  exit 0
fi

TARGET_URL="${ORCH_DYNAMIC_SCAN_TARGET:-http://127.0.0.1:8088}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not available for dynamic scan" >&2
  exit 1
fi

echo "==> Running OWASP ZAP baseline scan against ${TARGET_URL}"

docker run --rm -t owasp/zap2docker-stable zap-baseline.py \
  -t "$TARGET_URL" \
  -r zap_report.html || {
    echo "Dynamic scan completed with findings" >&2
    exit 1
  }

mv zap_report.html instance/zap_report.html

echo "OK: dynamic scan complete (report: instance/zap_report.html)"
