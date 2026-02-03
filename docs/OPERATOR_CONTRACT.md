# Operator Contract

This document defines what ORCHESTRATORS_V2 guarantees, what it does not guarantee, and what the operator must do to keep those guarantees true.

## Guarantees (when configured as documented)

- **Local-first execution**: With `NO_NETWORK=1` in tests, outbound network calls are blocked.
- **Policy-hash receipts**: Tool policy decisions are recorded with policy hash references for auditability.
- **Deterministic routing checks**: CI runs the test suite twice to surface nondeterminism.
- **Public boundary enforcement**: CI verifies that no runtime state or secrets are present.
- **HITL escalation**: Ambiguous or high-risk intent routes require human review.

## Non-Guarantees (explicitly out of scope)

- **Compromised host**: If the host OS is compromised, local-first claims do not hold.
- **Malicious operator**: A privileged operator can bypass controls.
- **Third-party model behavior**: Remote model providers may behave unpredictably.

## Operator Responsibilities

- **Authentication**: Set `ORCH_REQUIRE_BEARER=1` and rotate `ORCH_BEARER_TOKEN` regularly.
- **Policy enforcement**: Keep `ORCH_TOOL_POLICY_ENFORCE=1` in production.
- **Network controls**: For hard isolation, run the service on a restricted network namespace or host.
- **Secrets hygiene**: Never commit runtime databases or environment files.
- **Observability**: Monitor trace receipts and routing summaries after changes.
- **Trust Panel**: Enable only when needed; treat outputs as redacted metadata.

## Related Docs

- [Trust Panel](TRUST_PANEL.md)
- [LLM Provider Contract](LLM_PROVIDER_CONTRACT.md)
- [Production Readiness](PRODUCTION_READINESS.md)

## Durability Note (Postgres)

SQLite is the default for simplicity. The Postgres persistence test is skipped unless `ORCH_DATABASE_URL` is configured. Use Postgres when you need durability, concurrency, or multi-worker deployments.
