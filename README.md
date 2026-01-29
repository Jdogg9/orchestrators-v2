# ORCHESTRATORS_V2

[![CI](https://github.com/Jdogg9/orchestrators-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/Jdogg9/orchestrators-v2/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A reproducible, local-first reference implementation of the **Orchestrator** pattern:
a stable identity + routing + tools + optional memory, designed for *your* machine and *your* rules.

## What This Is / What This Is Not

**✅ IS:**
- Safe reference architecture for LLM orchestration
- Privacy-first patterns (no data exfiltration)
- Guardrails for secrets, state, and runtime isolation
- Extensible framework for tools, memory, routing

**❌ NOT:**
- A turnkey agent (you bring your own models/identity)
- A hosted service (runs locally only)
- A magic model (requires Ollama/OpenAI/etc.)

## Project Lineage (v1 → v2)

- **v1 (AIMEE_ORCHESTRATORS)**: Original research/prototype repo that explored the orchestrator pattern in production.
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
# Expected: {"status":"ok","server":"ORCHESTRATORS_V2"}

# 4. Verify no secrets leaked
./scripts/verify_public_boundary.sh
# Expected: ✅ PUBLIC BOUNDARY SAFE (5/5 checks passing)
```

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

## Quickstart (5 minutes)
```bash
cd ORCHESTRATORS_V2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.server
```

Server runs on `http://127.0.0.1:8088` with OpenAI-compatible shape (optional).

## Security Model (Defaults)

* **Local-first**: No cloud dependencies
* **No exfiltration**: Data stays on your machine
* **Feature flags**: Memory/recall/tools OFF by default
* **Runtime state**: Never committed (see [.gitignore](.gitignore))

## Documentation

- [Operational Philosophy](docs/OPERATIONAL_PHILOSOPHY.md) - **Why** we built it this way (bounded memory, receipts, rehearsals, defaults off, automation)
- [Architecture](docs/ARCHITECTURE.md) - Layer design (API → orchestrator → tools → persistence)
- [Threat Model](docs/THREAT_MODEL.md) - Security stance and mitigations
- [Public Release Guide](docs/PUBLIC_RELEASE_GUIDE.md) - Maintenance workflow

## Contributing

This is a reference implementation. Fork it, extend it, break it. Key extension points:
- `src/router.py` - Model selection logic
- `src/tools/` - Custom tool implementations
- `src/memory.py` - RAG/memory patterns (optional)

Run `./scripts/verify_public_boundary.sh` before committing to ensure no secrets leaked.
