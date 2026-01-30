#!/usr/bin/env bash
# Fail if obvious secrets are found in tracked, non-doc files.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v git >/dev/null 2>&1; then
  echo "git not found" >&2
  exit 1
fi

PATTERNS=(
  "sk-[A-Za-z0-9_-]{20,}"
  "ghp_[A-Za-z0-9_-]{36,}"
  "gho_[A-Za-z0-9_-]{36,}"
  "AIza[A-Za-z0-9_-]{35}"
  "xox[baprs]-[A-Za-z0-9_-]{10,}"
  "-----BEGIN [A-Z ]+ PRIVATE KEY-----"
)

EXCLUDE_REGEX='^(docs/|reports/|scripts/|tests/|\.github/|\.pytest_cache/|examples/)'

fail=0
while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  if [[ "$file" =~ $EXCLUDE_REGEX ]]; then
    continue
  fi

  for pattern in "${PATTERNS[@]}"; do
    if grep -n -E "$pattern" "$ROOT_DIR/$file" >/dev/null 2>&1; then
      echo "❌ Secret-like pattern found in $file: $pattern"
      fail=1
    fi
  done
done < <(git -C "$ROOT_DIR" ls-files)

if [[ $fail -ne 0 ]]; then
  echo "Secret scan failed. Remove secrets before publishing." >&2
  exit 1
fi

echo "✅ Secret scan passed."
