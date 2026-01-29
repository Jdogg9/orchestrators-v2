#!/usr/bin/env bash
# File: scripts/verify_public_boundary.sh
# Purpose: Pre-publish safety check - verify no private data leaked
# Run this BEFORE pushing to GitHub

set -euo pipefail

# Detect directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔍 PUBLIC BOUNDARY VERIFICATION"
echo "================================"
echo ""

EXIT_CODE=0

# Check 1: No forbidden patterns in code
echo "[1/5] Checking for forbidden patterns..."
FORBIDDEN=(
    "NEXUSSTL_API_KEY"
    "sk-[a-zA-Z0-9]{32,}"
    "/home/jay"
    "aimee_backups"
    "nexusstl.com"
    "cloudflared"
)

for pattern in "${FORBIDDEN[@]}"; do
    if grep -r -E "$pattern" "$PUBLIC" \
        --exclude-dir=.git \
        --exclude-dir=.venv \
        --exclude-dir=venv \
        --exclude-dir=__pycache__ \
        --exclude-dir=instance \
        --exclude="*.pyc" \
        --exclude=sanitize_strings.sh \
        --exclude=verify_public_boundary.sh \
        --exclude=import_patterns_from_private.sh \
        --exclude=safe_import_workflow.sh \
        --exclude=PUBLIC_RELEASE_GUIDE.md \
        --exclude=.gitignore \
        2>/dev/null; then
        echo "  ❌ FAIL: Found forbidden pattern: $pattern"
        EXIT_CODE=1
    fi
done
[[ $EXIT_CODE -eq 0 ]] && echo "  ✅ PASS: No forbidden patterns found (operational files excluded)"

# Check 2: No runtime state directories
echo ""
echo "[2/5] Checking for runtime state directories..."
RUNTIME_DIRS=(
    "$PUBLIC/instance"
    "$PUBLIC/logs"
    "$PUBLIC/backups"
    "$PUBLIC/recall_frames"
)

for dir in "${RUNTIME_DIRS[@]}"; do
    if [[ -d "$dir" ]] && [[ -n "$(ls -A "$dir" 2>/dev/null)" ]]; then
        echo "  ❌ FAIL: Runtime directory not empty: $dir"
        ls -la "$dir" | head -10
        EXIT_CODE=1
    fi
done
[[ $EXIT_CODE -eq 0 ]] && echo "  ✅ PASS: No runtime state found"

# Check 3: No database files
echo ""
echo "[3/5] Checking for database files..."
if find "$PUBLIC" -name "*.db" -o -name "*.sqlite*" | grep -v ".gitignore" | grep .; then
    echo "  ❌ FAIL: Found database files (should be gitignored)"
    EXIT_CODE=1
else
    echo "  ✅ PASS: No database files found"
fi

# Check 4: .env.example exists, .env does not
echo ""
echo "[4/5] Checking environment files..."
if [[ ! -f "$PUBLIC/.env.example" ]]; then
    echo "  ❌ FAIL: Missing .env.example"
    EXIT_CODE=1
elif [[ -f "$PUBLIC/.env" ]]; then
    echo "  ❌ FAIL: .env file exists (should be gitignored)"
    EXIT_CODE=1
else
    echo "  ✅ PASS: .env.example exists, .env properly ignored"
fi

# Check 5: .gitignore is comprehensive
echo ""
echo "[5/5] Checking .gitignore..."
REQUIRED_IGNORES=(
    ".env"
    "*.db"
    "instance/"
    "recall_frames/"
    "*.key"
    "*.pem"
)

MISSING=0
for pattern in "${REQUIRED_IGNORES[@]}"; do
    if ! grep -q "$pattern" "$PUBLIC/.gitignore" 2>/dev/null; then
        echo "  ⚠️  Missing .gitignore entry: $pattern"
        MISSING=1
    fi
done

if [[ $MISSING -eq 0 ]]; then
    echo "  ✅ PASS: .gitignore is comprehensive"
else
    echo "  ❌ FAIL: .gitignore missing critical patterns"
    EXIT_CODE=1
fi

# Summary
echo ""
echo "================================"
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ PUBLIC BOUNDARY SAFE"
    echo "   Ready to commit and push to GitHub"
else
    echo "❌ PUBLIC BOUNDARY VIOLATED"
    echo "   Fix issues above before publishing"
fi

exit $EXIT_CODE
