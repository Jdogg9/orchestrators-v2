#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$BASE_DIR/scripts/routing_report.sh"
