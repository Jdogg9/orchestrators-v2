#!/usr/bin/env bash
# File: scripts/import_patterns_from_private.sh
# Purpose: Selectively import architectural patterns from private ORCHESTRATOR to public ORCHESTRATORS_V2
# Safety: Allowlist-only, never copies runtime state or secrets

set -euo pipefail

# Detect project root (private repo)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC="$(cd "$SCRIPT_DIR/.." && pwd)"
PRIVATE="$(cd "$PUBLIC/../.." && pwd)"

echo "[*] Importing patterns from private to ORCHESTRATORS_V2 (allowlist-only)"

# ALLOWLIST: Files safe to copy (architecture patterns, no secrets/state)
ALLOWLIST=(
    # Core orchestration patterns (will be sanitized after copy)
    # "orchestrator_router.py:src/router.py"              # Model routing logic
    # "orchestrator_prompts.py:src/prompts.py"            # Prompt templates (sanitize identity)
    # "orchestrator_scrubber.py:src/scrubber.py"          # Secret redaction (safe pattern)
    
    # Hardening infrastructure (already generic)
    "scripts/sqlite_maintenance.py:scripts/sqlite_maintenance.py"   # DB maintenance pattern
    "scripts/systemd_onfailure_alert.sh:scripts/systemd_onfailure_alert.sh"  # Alert pattern
    
    # Documentation patterns (will be sanitized)
    # "docs/RUNBOOK.md:docs/RUNBOOK_TEMPLATE.md"   # Operational patterns
    # "HARDENING_PACK_PLAN.md:docs/HARDENING_GUIDE.md"  # Hardening philosophy
)

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
            return 1
        fi
    done
    
    # Create destination directory
    mkdir -p "$(dirname "$dst")"
    
    # Copy file
    cp "$src" "$dst"
    echo "✅ COPIED: $src → $dst"
}

# Import allowlisted files
for entry in "${ALLOWLIST[@]}"; do
    IFS=':' read -r src_rel dst_rel <<< "$entry"
    src="$PRIVATE/$src_rel"
    dst="$PUBLIC/$dst_rel"
    
    safe_copy "$src" "$dst" || true
done

echo ""
echo "[+] Pattern import complete."
echo "    Next: Run sanitize_strings.sh to remove private references"
