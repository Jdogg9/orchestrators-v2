# ORCHESTRATORS_V2

A reproducible, local-first reference implementation of the **Orchestrator** pattern:
a stable identity + routing + tools + optional memory, designed for *your* machine and *your* rules.

## Quickstart (5 minutes)
```bash
cd ORCHESTRATORS_V2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.server
```

## What this is

* A small HTTP service that exposes a chat endpoint (OpenAI-ish shape optional)
* A router that selects models (chat/tool/embed)
* A tool interface you can extend safely
* Optional memory + recall behind feature flags (OFF by default)

## What this is NOT

* Not a cloud service
* Not preconfigured with private identities
* Not shipping your runtime artifacts (DBs, frames, logs)

## Security model (defaults)

* Local-first
* No exfiltration by default
* Feature flags for anything sensitive (memory/recall/tools)
* Runtime state never committed

See `docs/` for architecture + threat model.
