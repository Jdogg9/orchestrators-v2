# Examples

Minimal, runnable demonstrations of the orchestrator pattern.

## Philosophy Alignment

All examples follow the 5 core principles:
- ✅ **Bounded Memory**: Explicit size limits (no unbounded growth)
- ✅ **Receipts**: Trace logs for every decision
- ✅ **Rehearsal**: Automated demo mode (`--auto` flag)
- ✅ **Defaults Off**: No persistence without explicit flags
- ✅ **Automation**: No manual intervention required

## Toy Orchestrator

**File**: [`toy_orchestrator.py`](toy_orchestrator.py)

A complete, working orchestrator in ~250 lines demonstrating:
- **2 tools**: Calculator (math eval), Echo (message repeat) via `ToolRegistry`
- **1 router**: Rule-based intent detection via `RuleRouter`
- **1 memory**: Bounded conversation history (max 10 messages)
- **1 loop**: Orchestrate → Route → Execute → Respond

⚠️ **Toy warning**: The calculator uses `eval()` on purpose. It includes a warning banner in code. Do not reuse this in production.
For a safe alternative, see [docs/SAFE_CALCULATOR.md](../docs/SAFE_CALCULATOR.md).

### Run Interactive Mode
```bash
python examples/toy_orchestrator.py

# Try these commands:
> calculate 2 + 2
> echo hello world
> trace          # Show decision trace
> memory         # Show conversation history
> quit
```

### Run Automated Demo
```bash
python examples/toy_orchestrator.py --auto
```

### Expected Output
```
📥 User: calculate 2 + 2
  🧭 [Router] Tool=calculator, Confidence=0.8
  🔧 [Tool] calculator() → Result: 4
  📊 [Memory] 2/10 messages
📤 Assistant: Result: 4
```

## What You'll Learn

1. **Routing Pattern**: How to detect intent and select tools
2. **Tool Execution**: How to call tools with validated parameters
3. **Bounded Memory**: How to enforce size limits (oldest evicted first)
4. **Receipt Generation**: How to trace every decision for debugging
5. **Local-First**: No network calls, pure Python, runs offline

## Anti-Patterns Avoided

This example does NOT:
- ❌ Use unbounded memory (explicit 10-message cap)
- ❌ Persist state (in-memory only)
- ❌ Make network calls (local-only)
- ❌ Auto-activate features (manual run required)
- ❌ Hide decisions (every step traced)

## Extending the Example

**Safe additions:**
- Add new tools (weather, time, search)
- Add better routers (embeddings, LLM-based)
- Add persistence layer (SQLite with TTL)
- Add dry-run mode (rehearsal principle)

**Remember**: 
- Keep tools bounded (timeouts, size limits)
- Add receipts (logs, traces, checksums)
- Default features off (explicit enablement)
- Test boundary (no secrets leaked)

## Next Steps

1. Run the toy orchestrator
2. Read the source code (~250 lines, heavily commented)
3. Extend with your own tools
4. Read [Operational Philosophy](../docs/OPERATIONAL_PHILOSOPHY.md) to understand "why"
5. Check [CONTRIBUTING.md](../CONTRIBUTING.md) to propose improvements

---

**Philosophy**: These aren't production examples. They're teaching tools demonstrating principles through minimal, readable code.
