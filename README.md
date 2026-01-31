# ORCHESTRATORS_V2

[![CI](https://github.com/Jdogg9/orchestrators-v2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Jdogg9/orchestrators-v2/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

✅ CI enforces public boundary + tests on every push/PR.

- 📄 Executive Summary: EXECUTIVE_SUMMARY.md  
- ✅ Production Action Plan: ACTION_PLAN.md

A reproducible, local-first reference implementation of the **Orchestrator** pattern:
a stable identity + routing + tools + optional memory, designed for *your* machine and *your* rules.

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

## Repo Facts (checked by tests)
<!-- REPO_FACTS_START -->
- **Server routes**: `/health`, `/ready`, `/metrics`, `/echo`, `/v1/chat/completions`, `/v1/tools/execute`, `/v1/agents`, `/v1/agents/<name>`, `/v1/agents/<name>/chat`
- **Default bind**: `ORCH_PORT=8088`, `ORCH_HOST=127.0.0.1`
- **API flag**: `ORCH_ENABLE_API`
- **Auth flags**: `ORCH_REQUIRE_BEARER`, `ORCH_BEARER_TOKEN`
- **LLM flags**: `ORCH_LLM_ENABLED`, `ORCH_LLM_PROVIDER`, `ORCH_OLLAMA_URL`, `ORCH_MODEL_CHAT`, `ORCH_LLM_TIMEOUT_SEC`, `ORCH_LLM_HEALTH_TIMEOUT_SEC`
- **Safety flags**: `ORCH_MAX_REQUEST_BYTES`, `ORCH_RATE_LIMIT_ENABLED`, `ORCH_RATE_LIMIT`, `ORCH_RATE_LIMIT_STORAGE_URL`, `ORCH_LOG_JSON`, `ORCH_LOG_LEVEL`, `ORCH_METRICS_ENABLED`
- **Routing flags**: `ORCH_ORCHESTRATOR_MODE`, `ORCH_ROUTER_POLICY_PATH`
- **DB flags**: `ORCH_DATABASE_URL`, `ORCH_DB_POOL_RECYCLE`
- **Sandbox flags**: `ORCH_TOOL_SANDBOX_ENABLED`, `ORCH_TOOL_SANDBOX_REQUIRED`, `ORCH_SANDBOX_IMAGE`, `ORCH_SANDBOX_TIMEOUT_SEC`, `ORCH_SANDBOX_MEMORY_MB`, `ORCH_SANDBOX_CPU`, `ORCH_SANDBOX_TOOL_DIR`
- **Tool policy flags**: `ORCH_TOOL_POLICY_ENFORCE`, `ORCH_TOOL_POLICY_PATH`
- **OTel flags**: `ORCH_OTEL_ENABLED`, `ORCH_OTEL_EXPORTER_OTLP_ENDPOINT`, `ORCH_SERVICE_NAME`
- **Trace flags**: `ORCH_TRACE_ENABLED`, `ORCH_TRACE_DB_PATH`
- **Memory flags**: `ORCH_MEMORY_ENABLED`, `ORCH_MEMORY_CAPTURE_ENABLED`, `ORCH_MEMORY_WRITE_POLICY`, `ORCH_MEMORY_CAPTURE_TTL_MINUTES`, `ORCH_MEMORY_DB_PATH`
- **SQLite tables**: `traces`, `trace_steps`, `memory_candidates`
- **Memory decision taxonomy**: `allow:explicit_intent`, `allow:dedupe_update`, `allow:capture_only`, `deny:feature_disabled`, `deny:policy_write_disabled`, `deny:no_explicit_intent`, `deny:scrubbed_too_short`, `deny:sensitive_content`, `deny:error`
- **Toy example**: `examples/toy_orchestrator.py` uses `eval()` and includes `WARNING: eval() is dangerous - toy example only!`
- **Non-goals**: not a cloud/SaaS platform; no autonomous multi-agent planning in core (policy routing is deterministic)
<!-- REPO_FACTS_END -->

**Note on `deny:sensitive_content`**: “Sensitive content” includes secret-like patterns (keys/tokens), credentials, and other disallowed persistence classes.

## Project Lineage (v1 → v2)

- **v1 (ORCHESTRATOR_V1)**: Original research/prototype repo that explored the orchestrator pattern in production.
  Private repo containing identity, runtime state, and battle-tested iterations.

- **v2 (ORCHESTRATORS_V2)**: Sanitized, reproducible reference implementation with safe defaults and boundary verification.
  This repo is designed for "bring-your-own-identity" and **does not** ship private prompts, runtime state, DBs, recall frames, or tokens.

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
```

## Try the Toy Orchestrator (5 minutes)

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

**What you'll see**: Bounded memory (10 msg cap), decision traces (receipts), local-only execution (no network).

**Read more**: [examples/README.md](examples/README.md) for architecture walkthrough.

⚠️ **Toy warning**: The calculator uses `eval()` by design for teaching. Do not reuse it in production. See [docs/SAFE_CALCULATOR.md](docs/SAFE_CALCULATOR.md) for an AST-based alternative.

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

## Security Model (Defaults)

* **Local-first**: No cloud dependencies
* **No exfiltration**: Data stays on your machine
* **Feature flags**: Memory/recall/tools OFF by default
* **Runtime state**: Never committed (see [.gitignore](.gitignore))

## Documentation

- [Operational Philosophy](docs/OPERATIONAL_PHILOSOPHY.md) - **Why** we built it this way (bounded memory, receipts, rehearsals, defaults off, automation)
- [Architecture](docs/ARCHITECTURE.md) - Layer design (API → orchestrator → tools → persistence)
- [Threat Model](docs/THREAT_MODEL.md) - Security stance and mitigations
- [Routing & Tools](docs/ROUTING_AND_TOOLS.md) - Tool registry + rule routing patterns
- [Production Readiness](docs/PRODUCTION_READINESS.md) - Gaps and hardening checklist
- [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md) - High-stakes stack
- [Security Governance](docs/SECURITY_GOVERNANCE.md) - Signed commits, branch protections, dynamic scans
- [Public Release Guide](docs/PUBLIC_RELEASE_GUIDE.md) - Maintenance workflow

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
