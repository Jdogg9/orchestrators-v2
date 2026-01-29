# Architecture (ORCHESTRATORS_V2)

## Layers

1. API layer (server)
2. Orchestrator (routing + governance hooks)
3. Tools (pluggable functions)
4. Optional persistence (memory/recall) behind flags

## Design goals

* Reproducible
* Local-first
* Safe defaults
* Extensible without refactoring core
