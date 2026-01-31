#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "==> Boundary check"
./scripts/verify_public_boundary.sh

echo "==> Secret scan"
./scripts/secret_scan.sh

echo "==> Security automation"
./scripts/security_scan.sh

echo "==> Signed commit verification (optional)"
./scripts/verify_signed_commits.sh

echo "==> Dynamic scan (optional)"
./scripts/dynamic_scan.sh

echo "==> Pytest"
pytest -q

echo "==> Cleanup runtime artifacts"
rm -f "$ROOT_DIR/instance/trace.db"

