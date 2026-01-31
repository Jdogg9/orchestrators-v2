#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR" || exit

rm -f instance/*.db

./scripts/verify_public_boundary.sh
./scripts/secret_scan.sh

pytest -q -k "repo_facts"
pytest -q

echo "OK: tests complete"