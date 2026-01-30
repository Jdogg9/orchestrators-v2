#!/usr/bin/env bash
# File: scripts/systemd_onfailure_alert.sh
# Purpose: Handle systemd service/timer failures with local-first alerting
# Usage: systemd_onfailure_alert.sh <service-name> <exit-code> [message]
# Called by: OnFailure= directive in systemd units

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

ALERT_LOG_PATH="${ALERT_LOG_PATH:-./logs/alerts.jsonl}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
ALERT_DESKTOP_NOTIFY="${ALERT_DESKTOP_NOTIFY:-1}"
RATE_LIMIT_FILE="/tmp/orchestrator-alert-rate-limit"
RATE_LIMIT_SECONDS=300  # 5 minutes

# Secret patterns to redact (regex)
SECRET_PATTERNS=(
    "orch_sk_[A-Za-z0-9]+"
    "sk-[A-Za-z0-9]{48}"
    "AIza[A-Za-z0-9_-]{35}"
)

# ============================================================================
# Logging
# ============================================================================

log_json() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "$@" | jq -c ". + {timestamp: \"$timestamp\"}"
}

ensure_log_dir() {
    local log_dir=$(dirname "$ALERT_LOG_PATH")
    mkdir -p "$log_dir"
}

# ============================================================================
# Rate Limiting
# ============================================================================

check_rate_limit() {
    local service="$1"
    local rate_limit_key="${RATE_LIMIT_FILE}.${service}"
    
    if [[ -f "$rate_limit_key" ]]; then
        local last_alert=$(cat "$rate_limit_key")
        local now=$(date +%s)
        local elapsed=$((now - last_alert))
        
        if [[ $elapsed -lt $RATE_LIMIT_SECONDS ]]; then
            log_json '{
                "event": "ALERT_RATE_LIMITED",
                "service": "'"$service"'",
                "elapsed_seconds": '"$elapsed"',
                "rate_limit_seconds": '"$RATE_LIMIT_SECONDS"'
            }' >> "$ALERT_LOG_PATH"
            return 1
        fi
    fi
    
    # Update rate limit timestamp
    date +%s > "$rate_limit_key"
    return 0
}

# ============================================================================
# Secret Scrubbing
# ============================================================================

scrub_secrets() {
    local text="$1"
    local scrubbed="$text"
    
    for pattern in "${SECRET_PATTERNS[@]}"; do
        scrubbed=$(echo "$scrubbed" | sed -E "s/${pattern}/[REDACTED]/g")
    done
    
    echo "$scrubbed"
}

# ============================================================================
# Alert Destinations
# ============================================================================

write_local_log() {
    local service="$1"
    local exit_code="$2"
    local message="$3"
    
    ensure_log_dir
    
    local scrubbed_message=$(scrub_secrets "$message")
    
    log_json '{
        "event": "SYSTEMD_FAILURE",
        "service": "'"$service"'",
        "exit_code": '"$exit_code"',
        "message": "'"$scrubbed_message"'",
        "action_required": "Check journalctl -u '"$service"' -n 50"
    }' >> "$ALERT_LOG_PATH"
}

send_desktop_notify() {
    local service="$1"
    local message="$2"
    
    if [[ "$ALERT_DESKTOP_NOTIFY" != "1" ]]; then
        return 0
    fi
    
    if ! command -v notify-send &> /dev/null; then
        return 0
    fi
    
    local scrubbed_message=$(scrub_secrets "$message")
    
    notify-send --urgency=critical \
                --app-name="Orchestrator Alert" \
                --icon=dialog-error \
                "Orchestrator Service Failure" \
                "Service: $service\n\n$scrubbed_message" 2>/dev/null || true
}

send_email() {
    local service="$1"
    local exit_code="$2"
    local message="$3"
    
    if [[ -z "$ALERT_EMAIL" ]]; then
        return 0
    fi
    
    if ! command -v mail &> /dev/null; then
        log_json '{
            "event": "ALERT_EMAIL_SKIP",
            "reason": "mail_command_not_found"
        }' >> "$ALERT_LOG_PATH"
        return 0
    fi
    
    local scrubbed_message=$(scrub_secrets "$message")
    local subject="Orchestrator Alert: $service failed (exit $exit_code)"
    
    {
        echo "Orchestrator System Alert"
        echo "==================="
        echo ""
        echo "Service: $service"
        echo "Exit Code: $exit_code"
        echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo ""
        echo "Message:"
        echo "$scrubbed_message"
        echo ""
        echo "Action Required:"
        echo "  Check logs: journalctl -u $service -n 50"
        echo ""
        echo "---"
        echo "This is an automated alert from the orchestrator hardening pack."
    } | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || {
        log_json '{
            "event": "ALERT_EMAIL_FAILED",
            "service": "'"$service"'",
            "email": "'"$ALERT_EMAIL"'"
        }' >> "$ALERT_LOG_PATH"
    }
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    if [[ $# -lt 2 ]]; then
        echo "Usage: $0 <service-name> <exit-code> [message]"
        exit 1
    fi
    
    local service="$1"
    local exit_code="$2"
    local message="${3:-Service failed with no specific error message}"
    
    # Check rate limit (prevents spam)
    if ! check_rate_limit "$service"; then
        exit 0
    fi
    
    # Always write to local log (primary destination)
    write_local_log "$service" "$exit_code" "$message"
    
    # Optional: desktop notification
    send_desktop_notify "$service" "$message"
    
    # Optional: email alert
    send_email "$service" "$exit_code" "$message"
    
    # Log alert completion
    log_json '{
        "event": "ALERT_SENT",
        "service": "'"$service"'",
        "destinations": ["local_log"' \
        $([ "$ALERT_DESKTOP_NOTIFY" == "1" ] && command -v notify-send &>/dev/null && echo ', "desktop_notify"') \
        $([ -n "$ALERT_EMAIL" ] && command -v mail &>/dev/null && echo ', "email"') \
        ']
    }' >> "$ALERT_LOG_PATH"
}

main "$@"
