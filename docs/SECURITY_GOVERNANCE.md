# Security Governance

This document captures repo-level controls that require platform configuration.

## Signed Commits (Optional)

- Enable local enforcement by setting `ORCH_REQUIRE_SIGNED_COMMITS=1`.
- Run: `./scripts/verify_signed_commits.sh`
- CI can run this script, but it is intentionally opt-in.

## Branch Protections (GitHub Settings)

Recommended protections for `main`:

- Require pull requests before merging.
- Require status checks (CI, secret scan, security scan).
- Require signed commits.
- Require linear history.
- Restrict force pushes and deletions.

## Dynamic Scanning (Optional)

- Set `ORCH_DYNAMIC_SCAN_ENABLED=1` and `ORCH_DYNAMIC_SCAN_TARGET`.
- Run: `./scripts/dynamic_scan.sh`
- Requires Docker (uses OWASP ZAP baseline).

## CI Security Automation

- `scripts/security_scan.sh` runs Bandit + pip-audit by default.
- Semgrep and Trivy run if available.
- Secret scanning uses `scripts/secret_scan.sh`.
