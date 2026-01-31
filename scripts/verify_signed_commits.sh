#!/usr/bin/env bash
set -euo pipefail

if [ "${ORCH_REQUIRE_SIGNED_COMMITS:-0}" != "1" ]; then
  echo "Signed commit enforcement disabled (ORCH_REQUIRE_SIGNED_COMMITS!=1)"
  exit 0
fi

echo "==> Verifying signed commits"

missing=0
while read -r commit; do
  if ! git verify-commit "$commit" >/dev/null 2>&1; then
    echo "ERROR: unsigned or unverifiable commit $commit" >&2
    missing=1
  fi
done < <(git rev-list --all)

if [ "$missing" -ne 0 ]; then
  exit 1
fi

echo "OK: all commits are signed"
