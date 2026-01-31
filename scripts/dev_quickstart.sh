#!/usr/bin/env bash
set -euo pipefail

echo "== Orchestrators-v2 Dev Quickstart =="

python -m pip install --upgrade pip
pip install -r requirements.txt

./scripts/verify_public_boundary.sh
./scripts/secret_scan.sh

pytest -q

echo "PASS: dev quickstart complete"
