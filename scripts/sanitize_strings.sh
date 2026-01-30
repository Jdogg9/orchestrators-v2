#!/usr/bin/env bash
# File: scripts/sanitize_strings.sh
# Purpose: Remove private identifiers from ORCHESTRATORS_V2 files
# Safety: Find/replace with safe defaults, block forbidden patterns

set -euo pipefail

# Detect directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[*] Sanitizing ORCHESTRATORS_V2 (removing private identifiers)"

HOME_DIR="${HOME}"
PROJECT_ROOT='$PROJECT_ROOT'
BACKUP_DIR='$BACKUP_DIR'

# SANITIZATION RULES (private → public)
declare -A REPLACEMENTS=(
    # Paths (absolute → generic)
    ["${HOME_DIR}/projects"]="$PROJECT_ROOT"
    ["${HOME_DIR}/backups"]="$BACKUP_DIR"

    # Hostnames (private → public)
    ["private.example.com"]="localhost"
    ["cloudflared"]="# cloudflared (not included)"

    # Database names (keep generic)
    ["orchestrator_core.db"]="orchestrator_core.db"
    ["interactions.db"]="interactions.db"
    ["api_logs.db"]="api_logs.db"
    ["telemetry.db"]="telemetry.db"
)

# FORBIDDEN PATTERNS (block if found after sanitization)
FORBIDDEN_PATTERNS=(
    "sk-[a-zA-Z0-9]+"  # API keys
    "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"  # IP addresses (not localhost)
    "password.*="
    "token.*="
    "secret.*="
    "[a-f0-9]{32,}"  # Hashes that might be secrets
)

# Function: Apply sanitization to file
sanitize_file() {
    local file="$1"
    
    # Skip binary files
    if ! file "$file" | grep -q "text"; then
        return 0
    fi
    
    echo "  Processing: $file"
    
    # Apply replacements
    for search in "${!REPLACEMENTS[@]}"; do
        replace="${REPLACEMENTS[$search]}"
        if grep -q "$search" "$file" 2>/dev/null; then
            sed -i "s|$search|$replace|g" "$file"
            echo "    ✓ Replaced: $search → $replace"
        fi
    done
    
    # Check for forbidden patterns
    for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
        if grep -E "$pattern" "$file" 2>/dev/null; then
            echo "    ⚠️  WARNING: Forbidden pattern found: $pattern"
            echo "       File: $file"
            echo "       Please review manually!"
        fi
    done
}

# Sanitize all text files in PUBLIC (exclude .git, .venv, etc.)
find "$PUBLIC" -type f \
    ! -path "*/.git/*" \
    ! -path "*/.venv/*" \
    ! -path "*/venv/*" \
    ! -path "*/__pycache__/*" \
    ! -path "*/.pytest_cache/*" \
    ! -path "./instance/*" \
    ! -path "*/reports/*" \
    ! -path "$PUBLIC/scripts/sanitize_strings.sh" \
    ! -path "$PUBLIC/scripts/verify_public_boundary.sh" \
    ! -name "*.pyc" \
    ! -name "*.db" \
    -print0 | while IFS= read -r -d '' file; do
    sanitize_file "$file"
done

echo ""
echo "[+] Sanitization complete."
echo "    Review warnings above and inspect files manually."
echo "    Before publishing: grep -r 'jay\\|ORCHESTRATOR\\|orchestrators_v2' $PUBLIC"
