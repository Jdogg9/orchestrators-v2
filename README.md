# ORCHESTRATORS_V2

[![CI](https://github.com/Jdogg9/orchestrators-v2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Jdogg9/orchestrators-v2/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ORCHESTRATORS_V2 is a privacy-first orchestration framework with production-oriented guardrails and safety-first defaults.**
It runs locally, keeps data on your machine, and emits auditable receipts so you can prove what happened.
You get deterministic routing + tools without turning into a sprawling framework.

✅ CI enforces public boundary + tests on every push/PR.

- 📄 Executive Summary: EXECUTIVE_SUMMARY.md  
- ✅ Production Action Plan: ACTION_PLAN.md
- 🧭 Intent Router: docs/INTENT_ROUTER.md
- 🧾 Operator Contract: docs/OPERATOR_CONTRACT.md

A reproducible, local-first **privacy-first orchestration framework** with production-oriented guardrails and safety-first defaults
for a stable identity + routing + tools + optional memory, designed for *your* machine and *your* rules.

## Why this is different

- **Token-aware safety**: deterministic token budgets, tiered reasoning (4k / 32k / 32k+), and priority-aware pruning with receipt-backed telemetry.
- **Graceful degradation**: tokenizer fallback preserves safety logic even when optional dependencies are unavailable.
- **Boundary-first posture**: public boundary verification is a first-class release gate.

## Tokenization

Token accounting uses a local-first tokenizer with a byte-level fallback to maintain safety even
when optional dependencies are missing.

**New for Jan 2026:** Now featuring Semantic Truncation and OTel-compatible Token Health telemetry.

## Observability & Compliance

Orchestrators-v2 aligns with NIST AI RMF expectations by providing measurable, exportable metrics
that demonstrate bounded context behavior and safe routing decisions:

- **Token utilization ratio** for context budget accountability.
- **Tier transition counts** to show how often the router escalates to reasoner or summary modes.
- **Semantic truncation delta** to prove instruction coherence under pruning pressure.

These metrics are Prometheus-compatible and can be surfaced in Grafana dashboards for audit readiness.

## Security Transparency (Jan 2026 Remediation)

Our Jan 2026 remediation cycle demonstrates reachability-first risk management without breaking routing integrity:

- **Reachability analysis first**: vulnerabilities in unreachable code paths are logged as accepted risks to maintain deterministic behavior.
- **Mitigation by architecture**: AST-safe evaluators, tool_policy.yaml validation, and sandboxed execution limit exploitability even when advisories exist.
- **Audit-ready exports**: JSON-LD and PDF compliance reports include dependency health summaries tied to NIST Measure 2.1.

This approach protects user data sovereignty by ensuring patches do not compromise safety invariants or leak runtime state.

## Why not LangGraph / CrewAI?

No dunking—just different assumptions:

- **Data exfiltration risk**: Orchestrators-v2 assumes local-only by default; many multi-agent stacks assume cloud connectivity.
- **Boundary verification**: This repo ships scripts that verify no runtime state or secrets are present before publishing.
- **Auditable receipts**: Trace receipts (DB + logs) are first-class to support operator review and change tracking.

### Privacy/Security-Oriented Comparison

| Capability | Orchestrators-v2 | Typical multi-agent framework |
| --- | --- | --- |
| Local-first default | ✅ | ⚠️ Depends on setup |
| Offline operation | ✅ | ⚠️ Limited/optional |
| Boundary verification scripts | ✅ | ❌ | 
| Audit receipts (trace DB/logs) | ✅ | ⚠️ Varies |
| Human-governance hooks | ✅ | ⚠️ Varies |
| Supply chain hygiene (pinning/checks) | ✅ | ⚠️ Varies |

## What This Is / What This Is Not

**✅ IS:**
- Safe reference architecture for LLM orchestration
- Privacy-first patterns (no data exfiltration)
- Guardrails for secrets, state, and runtime isolation
- Extensible framework for tools, memory, routing
- A turnkey agent as a hosted service (runs locally only) — verified in the 30-Second Proof below
- Ships with a starter agent named **Holly** (optional default, fully modifiable)

**❌ NOT:**
- A cloud/SaaS platform (this runs locally only)
- A magic model (requires Ollama/OpenAI/etc.)

## V2.0 Stable: Defensive AI Engineering

This release hardens the orchestrator with confidence-gated routing and policy-enforced execution.

- **Semantic Ambiguity Guard**: blocks unclear intent when top candidates are too close.
- **Conditional Approvals**: length-gated tool access in `tool_policy.yaml` prevents oversized/malicious inputs.
- **Top-K Diagnostics**: traces now record the highest semantic matches for auditability.
- **Hardened Sandbox**: `python_exec` runs isolated with strict resource limits.
- **Expanded Tools**: built-in summarization plus optional web search (opt-in).

These layers shift the system from “works” to “safe to leave unattended.”

**Storage note:** SQLite is the default for simplicity; the Postgres persistence test is skipped unless `ORCH_DATABASE_URL` is configured. Use Postgres when you need durability, concurrency, or multi-worker deployments.

## Repo Facts (checked by tests)
<!-- REPO_FACTS_START -->
- **Server routes**: `/health`, `/ready`, `/metrics`, `/echo`, `/v1/chat/completions`, `/v1/tools/execute`, `/v1/agents`, `/v1/agents/<name>`, `/v1/agents/<name>/chat`, `/v1/audit/verify`
- **Default bind**: `ORCH_PORT=8088`, `ORCH_HOST=127.0.0.1`
- **Environment flag**: `ORCH_ENV`
- **API flag**: `ORCH_ENABLE_API`
- **Auth flags**: `ORCH_REQUIRE_BEARER`, `ORCH_BEARER_TOKEN`
- **LLM flags**: `ORCH_LLM_ENABLED`, `ORCH_LLM_PROVIDER`, `ORCH_OLLAMA_URL`, `ORCH_MODEL_CHAT`, `ORCH_LLM_TIMEOUT_SEC`, `ORCH_LLM_HEALTH_TIMEOUT_SEC`
- **Safety flags**: `ORCH_MAX_REQUEST_BYTES`, `ORCH_RATE_LIMIT_ENABLED`, `ORCH_RATE_LIMIT`, `ORCH_RATE_LIMIT_STORAGE_URL`, `ORCH_LOG_JSON`, `ORCH_LOG_LEVEL`, `ORCH_METRICS_ENABLED`
- **Routing flags**: `ORCH_ORCHESTRATOR_MODE`, `ORCH_ROUTER_POLICY_PATH`, `ORCH_INTENT_ROUTER_ENABLED`, `ORCH_INTENT_ROUTER_SHADOW`, `ORCH_INTENT_DECISION_EXPOSE`
- **Semantic routing flags**: `ORCH_SEMANTIC_ROUTER_ENABLED`, `ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY`, `ORCH_SEMANTIC_ROUTER_EMBED_MODEL`, `ORCH_SEMANTIC_ROUTER_OLLAMA_URL`, `ORCH_SEMANTIC_ROUTER_TIMEOUT_SEC`
- **Intent routing flags**: `ORCH_INTENT_MIN_CONFIDENCE`, `ORCH_INTENT_MIN_GAP`, `ORCH_INTENT_CACHE_ENABLED`, `ORCH_INTENT_CACHE_DB_PATH`, `ORCH_INTENT_CACHE_TTL_SEC`, `ORCH_INTENT_HITL_ENABLED`, `ORCH_INTENT_HITL_DB_PATH`
- **DB flags**: `ORCH_DATABASE_URL`, `ORCH_DB_POOL_RECYCLE`, `ORCH_SQLITE_WAL_ENABLED`
- **Sandbox flags**: `ORCH_TOOL_SANDBOX_ENABLED`, `ORCH_TOOL_SANDBOX_REQUIRED`, `ORCH_TOOL_SANDBOX_FALLBACK`, `ORCH_SANDBOX_IMAGE`, `ORCH_SANDBOX_TIMEOUT_SEC`, `ORCH_SANDBOX_MEMORY_MB`, `ORCH_SANDBOX_CPU`, `ORCH_SANDBOX_TOOL_DIR`
- **Tool policy flags**: `ORCH_TOOL_POLICY_ENFORCE`, `ORCH_TOOL_POLICY_PATH`
- **Tool feature flags**: `ORCH_TOOL_WEB_SEARCH_ENABLED`
- **Tool output flags**: `ORCH_TOOL_OUTPUT_MAX_CHARS`, `ORCH_TOOL_OUTPUT_SCRUB_ENABLED`, `ORCH_POLICY_DECISIONS_IN_RESPONSE`
- **OTel flags**: `ORCH_OTEL_ENABLED`, `ORCH_OTEL_EXPORTER_OTLP_ENDPOINT`, `ORCH_SERVICE_NAME`
- **Trace flags**: `ORCH_TRACE_ENABLED`, `ORCH_TRACE_DB_PATH`
- **Memory flags**: `ORCH_MEMORY_ENABLED`, `ORCH_MEMORY_CAPTURE_ENABLED`, `ORCH_MEMORY_WRITE_POLICY`, `ORCH_MEMORY_CAPTURE_TTL_MINUTES`, `ORCH_MEMORY_DB_PATH`, `ORCH_MEMORY_SCRUB_REDACT_PII`
- **SQLite tables**: `traces`, `trace_steps`, `memory_candidates`, `intent_cache`, `hitl_queue`
- **Memory decision taxonomy**: `allow:explicit_intent`, `allow:dedupe_update`, `allow:capture_only`, `deny:feature_disabled`, `deny:policy_write_disabled`, `deny:no_explicit_intent`, `deny:scrubbed_too_short`, `deny:sensitive_content`, `deny:error`
- **Toy example**: `examples/toy_orchestrator.py` uses an AST-safe evaluator (no `eval`).
- **Non-goals**: not a cloud/SaaS platform; no autonomous multi-agent planning in core (policy routing is deterministic)
<!-- REPO_FACTS_END -->

**Note on `deny:sensitive_content`**: “Sensitive content” includes secret-like patterns (keys/tokens), credentials, and other disallowed persistence classes.

## Project Lineage (v1 → v2)

- **v1 (ORCHESTRATOR_V1)**: Original research/prototype repo that explored the orchestrator pattern in production.
  Private repo containing identity, runtime state, and battle-tested iterations.

- **v2 (ORCHESTRATORS_V2)**: Sanitized, reproducible privacy-first framework with safety-first defaults and boundary verification.
  This repo is the **V2.0 Stable baseline** for production-oriented orchestration and "bring-your-own-identity" deployments.
  It **does not** ship private prompts, runtime state, DBs, recall frames, or tokens.

If you want conceptual background + earlier experiments, v1 is the source.
If you want the safe public baseline to fork and extend, **use v2**.

## 30-Second Proof

```bash
# 1. Setup (one command)
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 2. Run server
cp .env.example .env  # Uses safe defaults
python -m src.server &

# 3. Health check
curl http://127.0.0.1:8088/health
# Expected: {"status":"ok","service":"orchestrators_v2"}

# 3b. Readiness check
curl http://127.0.0.1:8088/ready
# Expected: {"status":"ready","service":"orchestrators_v2"}

# 3c. Starter agent proof (Holly)
curl http://127.0.0.1:8088/v1/agents/holly
# Expected: {"name":"Holly", ...}

curl -X POST http://127.0.0.1:8088/v1/agents/holly/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello, Holly"}]}'
# Expected: assistant response (stub or LLM-backed)

**Auth policy:** When `ORCH_REQUIRE_BEARER=1`, `/v1/chat/completions` and `/metrics` require a valid `Authorization: Bearer …` token; `/health` and `/ready` remain unauthenticated for local probes.

# 4. Verify no secrets leaked
./scripts/verify_public_boundary.sh
# Expected: ✅ PUBLIC BOUNDARY SAFE (5/5 checks passing)

# 5. Full receipts bundle (boundary + secrets + tests)
./scripts/verify.sh

**CI preflight:** Run these locally before pushing to match the CI gates and order.

**Shortcut:** `./scripts/dev_quickstart.sh`

**One-command test runner:** `./scripts/run_tests.sh`

**CI routing report:** Each PR uploads a `ci-routing-report` artifact with golden-case count, tier distribution, mismatch counts, and HITL rate.
Generate locally with `make routing-report` or `./scripts/routing_report.sh`.

```bash
# CI preflight (mirrors .github/workflows/ci.yml order)
python -m pip install --upgrade pip
pip install -r requirements.txt

./scripts/verify_public_boundary.sh
./scripts/secret_scan.sh

pytest -q -k "repo_facts"
pytest -q

# Optional: run script lint locally if you have shellcheck installed
shellcheck -e SC2155 -e SC2046 -e SC2012 ./scripts/*.sh
```

**Targeted safety tests (semantic routing + sandbox):**

```bash
pytest -q tests/test_semantic_router.py tests/test_sandbox.py tests/test_tool_policy_conditions.py
```
```

## Killer Demo (Local Receipts + Boundary Verification)

Run the philosophy end-to-end in minutes:

- [Killer demo quickstart](examples/killer_demo_local_receipts/README.md)

## Hardened Full Stack (one command)

Spin up sandboxing + Postgres + Redis + metrics in one shot:

```bash
cp .env.production.example .env.production
# Rotate ORCH_BEARER_TOKEN before production use.

docker compose -f docker-compose.full.yml up --build
```

See [docs/OBSERVABILITY_STACK.md](docs/OBSERVABILITY_STACK.md) for dashboards and alerts.

## Try the Orchestrator (5 minutes)

A minimal, runnable example demonstrating the full pattern:

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run interactive mode
python examples/toy_orchestrator.py

# Try commands:
> calculate 2 + 2
> echo hello world
> trace    # Show decision trace
> memory   # Show conversation history
```

**What you'll see**:
* **Safe Math**: Calculations use an AST-safe evaluator (no `eval()`).
* **Bounded Memory**: Conversation history is capped at 10 messages.
* **Trace Receipts**: Every decision is logged with receipt-style traces.

**Read more**: [examples/README.md](examples/README.md) for architecture walkthrough.

✅ **Safe Math**: The calculator uses a restricted AST-based evaluator (no `eval`) to prevent code injection. See [docs/SAFE_CALCULATOR.md](docs/SAFE_CALCULATOR.md).

## Example Orchestrator Loop

```python
# Pseudo-code demonstrating the pattern
def orchestrate(user_request):
    # 1. Router chooses appropriate tool/model
    route = router.select(user_request)
    
    # 2. Tool executes with guardrails
    result = tools.execute(route.tool, route.params, 
                           scrub_secrets=True,
                           log_usage=True)
    
    # 3. Response returned (state never persisted by default)
    return {"response": result, "route": route.name}
```

## Quickstart (API Server)
```bash
cd ORCHESTRATORS_V2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.server
```

Server runs on `http://127.0.0.1:8088` with OpenAI-compatible shape (optional).

## Quickstart (Docker)
```bash
cp .env.example .env
docker compose up --build
```

Server runs on `http://127.0.0.1:8088` and stays local-only by default.

## Deployment Artifacts (Hardened Defaults)

- Dockerfile + compose: `Dockerfile`, `docker-compose.yml`
- Production compose: `deploy/docker-compose.prod.yml`
- Gunicorn config: `gunicorn.conf.py`
- Systemd unit template: `deploy/systemd/orchestrators-v2.service`
- Secret scan (CI): `scripts/secret_scan.sh`
- Security automation: `scripts/security_scan.sh`
- Postgres schema init: `scripts/init_postgres_schema.py`
- SQLite → Postgres migration: `scripts/migrate_sqlite_to_postgres.py`

## Security Model (Defaults)

* **Local-first**: No cloud dependencies
* **No exfiltration**: Data stays on your machine
* **Feature flags**: Memory/recall/tools OFF by default
* **Runtime state**: Never committed (see [.gitignore](.gitignore))
* **Rate limits**: keyed by bearer token hash when provided (falls back to IP)
* **Auth**: bearer token required for all non-health endpoints in production

**Rate limit storage**: If `ORCH_RATE_LIMIT_STORAGE_URL` is not set, limits are per-process. For multi-worker or production use, Redis is strongly recommended.

**Token rotation**: update `ORCH_BEARER_TOKEN`, restart the service, and expire old tokens. Rotate on a fixed cadence (e.g., monthly) or after any incident.

## Documentation

- [Operational Philosophy](docs/OPERATIONAL_PHILOSOPHY.md) - **Why** we built it this way (bounded memory, receipts, rehearsals, defaults off, automation)
- [Architecture](docs/ARCHITECTURE.md) - Layer design (API → orchestrator → tools → persistence)
- [Unavoidable Architecture](docs/UNAVOIDABLE_ARCHITECTURE.md) - The definitive safety-first blueprint
- [Industry Leader Review (Jan 2026)](docs/INDUSTRY_REVIEW_JAN_2026.md) - Executive assessment of the release
- [Threat Model](docs/THREAT_MODEL.md) - Security stance and mitigations
- [Compliance Story](docs/COMPLIANCE_STORY.md) - What gets logged, receipts, offline ops
- [Interop & Migration](docs/INTEROP_AND_MIGRATION.md) - Mapping from LangGraph/CrewAI concepts
- [Routing & Tools](docs/ROUTING_AND_TOOLS.md) - Tool registry + rule routing patterns
- [Semantic Router Operator Guide](docs/SEMANTIC_ROUTER_OPERATIONS.md) - Tuning guidance and trace queries
- [Production Readiness](docs/PRODUCTION_READINESS.md) - Gaps and hardening checklist
- [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md) - High-stakes stack
- [Security Governance](docs/SECURITY_GOVERNANCE.md) - Signed commits, branch protections, dynamic scans
- [Public Release Guide](docs/PUBLIC_RELEASE_GUIDE.md) - Maintenance workflow
- [Observability Stack](docs/OBSERVABILITY_STACK.md) - OTel + Prometheus + Grafana
- [Trust Pack](trust_pack/README.md) - Operator checklist, audit template, deployment recipes
- [Community](docs/COMMUNITY.md) - Contribution channels + governance
- [Optional Modules](docs/OPTIONAL_MODULES.md) - Planning, scheduling, cost-aware routing

## Contributing

We welcome contributions that align with our [5 core principles](docs/OPERATIONAL_PHILOSOPHY.md).

**Before contributing**:
1. Read [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow and standards
2. Read [Operational Philosophy](docs/OPERATIONAL_PHILOSOPHY.md) - Understand the "why"
3. Run boundary checks: `./scripts/verify_public_boundary.sh`

**Current shipped structure**:
- `src/server.py` - Flask API stub (routes + memory capture decision)
- `src/memory.py` - Memory capture logic + taxonomy
- `src/orchestrator_memory.py` - Memory decision evaluation
- `src/tracer.py` - Trace store + steps
- `examples/` - Teaching examples

**Recommended extension structure (optional, not shipped by default)**:
- `src/routers/` - Model selection logic
- `src/tools/` - Custom tool implementations
- `src/memory/` - Additional memory backends

**Philosophy alignment required**: Feature requests must answer [5 questions](.github/ISSUE_TEMPLATE/feature_request.md) about bounded memory, receipts, rehearsal, defaults, and automation.

**High bar**: We resist feature creep and protect core principles.
