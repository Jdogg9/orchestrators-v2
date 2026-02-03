#!/usr/bin/env bash
set -euo pipefail

if [[ "${ORCH_LLM_ENABLED:-0}" != "1" ]]; then
  echo "LLM enablement check: ORCH_LLM_ENABLED!=1 (skipping)"
  exit 0
fi

fail() {
  echo "LLM enablement check failed: $1" >&2
  exit 1
}

require_set() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" ]]; then
    fail "${name} is required when ORCH_LLM_ENABLED=1"
  fi
}

require_set "ORCH_LLM_PROVIDER"
require_set "ORCH_LLM_TIMEOUT_SEC"
require_set "ORCH_LLM_HEALTH_TIMEOUT_SEC"
require_set "ORCH_LLM_MAX_OUTPUT_CHARS"
require_set "ORCH_LLM_RETRY_COUNT"
require_set "ORCH_LLM_RETRY_BACKOFF_SEC"
require_set "ORCH_LLM_CIRCUIT_MAX_FAILURES"
require_set "ORCH_LLM_CIRCUIT_RESET_SEC"

if [[ "${ORCH_TRACE_ENABLED:-0}" != "1" ]]; then
  fail "ORCH_TRACE_ENABLED must be 1 for receipted provider calls"
fi

if [[ "${ORCH_LLM_NETWORK_ENABLED:-0}" != "1" ]]; then
  fail "ORCH_LLM_NETWORK_ENABLED must be 1 to allow provider calls"
fi

provider="${ORCH_LLM_PROVIDER:-}"
if [[ "$provider" == "ollama" ]]; then
  require_set "ORCH_OLLAMA_URL"
fi

echo "LLM enablement check: OK"