#!/usr/bin/env bash
# File: scripts/import_patterns_from_private.sh
# Purpose: Mirror allowlisted files from private AIMEE repo to public ORCHESTRATORS_V2
# Safety: Allowlist-only (manifest-driven), never copies runtime state or secrets

set -euo pipefail

# Detect project root (private repo)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC="$(cd "$SCRIPT_DIR/.." && pwd)"
PRIVATE="$(cd "$PUBLIC/../.." && pwd)"

echo "[*] Mirroring allowlisted files from private to ORCHESTRATORS_V2 (manifest-driven)"

MANIFEST="$PUBLIC/scripts/mirror_manifest.txt"
if [[ ! -f "$MANIFEST" ]]; then
    echo "🛑 ERROR: Mirror manifest not found: $MANIFEST"
    exit 1
fi

# BLOCKLIST: Never copy these (secrets, state, identity, runtime)
BLOCKLIST_PATTERNS=(
    "*.db"
    "*.sqlite*"
    ".env"
    "recall_frames/"
    "instance/"
    "backups/"
    "*_SIGNOFF.md"
    "release_snapshot.json"
    "evidence_bundles/"
    "*ORCHESTRATOR*identity*"
    "*credentials*"
    "*.log"
    "*.key"
    "*.pem"
    "*.token"
)

# Function: Safe copy with verification
safe_copy() {
    local src="$1"
    local dst="$2"
    
    # Verify source exists
    if [[ ! -f "$src" ]]; then
        echo "⚠️  SKIP: $src (not found)"
        return 1
    fi
    
    # Check blocklist patterns
    for pattern in "${BLOCKLIST_PATTERNS[@]}"; do
        if [[ "$src" == *"$pattern"* ]]; then
            echo "🛑 BLOCKED: $src (matches blocklist pattern: $pattern)"
            blocked=$((blocked + 1))
            return 1
        fi
    done
    
    # Create destination directory
    mkdir -p "$(dirname "$dst")"
    
    # Copy file
    cp "$src" "$dst"
    echo "✅ COPIED: $src → $dst"
}

copied=0
skipped=0
blocked=0

# Import allowlisted files from manifest
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    IFS=':' read -r src_rel dst_rel <<< "$line"
    if [[ -z "$src_rel" || -z "$dst_rel" ]]; then
        echo "⚠️  SKIP: Invalid manifest entry: $line"
        skipped=$((skipped + 1))
        continue
    fi

    src="$PRIVATE/$src_rel"
    dst="$PUBLIC/$dst_rel"

    if safe_copy "$src" "$dst"; then
        copied=$((copied + 1))
    else
        skipped=$((skipped + 1))
    fi
done < "$MANIFEST"

echo ""
echo "[+] Mirror import complete."
echo "    Copied: $copied | Skipped: $skipped | Blocked: $blocked"
echo "    Next: Run sanitize_strings.sh to remove private references"
