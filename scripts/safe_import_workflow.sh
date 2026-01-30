#!/usr/bin/env bash
# Safe import workflow: import → sanitize → verify → review

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V2="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$V2"

echo "==[1/6] Confirm we're in ORCHESTRATORS_V2 =="
pwd
test -f README.md
test -f .env.example
test -f .gitignore

echo ""
echo "==[2/6] Run mirror import (manifest allowlist) =="
./scripts/import_patterns_from_private.sh

echo ""
echo "==[3/6] Sanitize private identifiers =="
./scripts/sanitize_strings.sh

echo ""
echo "==[4/6] Verify public boundary (MUST PASS) =="
./scripts/verify_public_boundary.sh

echo ""
echo "==[5/6] Show what would be committed (no commit yet) =="
git status --porcelain 2>/dev/null || echo "(git not initialized yet - this is OK)"
echo ""
echo "---- Potentially sensitive greps (should return nothing scary) ----"
grep -Rni --binary-files=without-match -E \
  "private_user|private_id|AIza|sk-|BEGIN (RSA|OPENSSH) PRIVATE KEY|tunnel|recall_memory\.db|release_snapshot" \
  . 2>/dev/null || echo "(no sensitive patterns found - GOOD)"

echo ""
echo "==[6/6] Preview tree of V2 =="
find . -maxdepth 3 -type f | sed 's|^\./||' | sort
echo ""
echo "DONE: Import+sanitize+verify complete. Review git status + grep results before committing."
