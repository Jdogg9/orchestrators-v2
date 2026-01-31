# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| 2.0.x | ✅ |

## Reporting a Vulnerability

Please report security issues via GitHub Security Advisories.

- Open a draft advisory in this repository.
- Include a clear description, reproduction steps, and any relevant logs.
- We will acknowledge receipt within 72 hours and provide a remediation plan or risk acceptance decision.

## Reachability Analysis (Jan 2026 Advisories)

For the January 2026 cycle, we performed reachability analysis on all Dependabot alerts and mapped each advisory to architectural controls:

- Hardened Gunicorn/Flask configuration with `debug=False` enforced.
- AST-safe evaluators and Docker-based sandboxing for tool execution.
- Strict input scrubbing and length-gated typed parameter mapping via tool policies.

This reachability evidence is captured in instance/vulnerability_log.json (local-only) and summarized in compliance exports for NIST AI RMF Measure 2.1.
