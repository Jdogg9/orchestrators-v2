#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR" || exit

echo "==> Boundary check"
./scripts/verify_public_boundary.sh

echo "==> Secret scan"
./scripts/secret_scan.sh

echo "==> Security automation"
./scripts/security_scan.sh

echo "==> Spellcheck (codespell)"
codespell

echo "==> Signed commit verification (optional)"
./scripts/verify_signed_commits.sh

echo "==> Dynamic scan (optional)"
./scripts/dynamic_scan.sh

echo "==> LLM enablement check (conditional)"
if [[ "${ORCH_LLM_ENABLED:-0}" == "1" ]]; then
	./scripts/verify_llm_enablement.sh
else
	echo "LLM enablement check skipped (ORCH_LLM_ENABLED!=1)"
fi

echo "==> Pytest"
pytest -q

echo "==> Cleanup runtime artifacts"
rm -f "$ROOT_DIR/instance/trace.db"

