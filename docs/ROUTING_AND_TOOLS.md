# Routing & Tools

This repo ships a minimal **tool registry**, **rule router**, and an optional **policy router** for production routing.

## Tool Registry (src/tool_registry.py)

- `ToolRegistry` stores `ToolSpec` entries (name, description, handler).
- `execute()` returns a structured result (`status`, `result` or `error`).
- Unsafe tools can be forced through a Docker sandbox via `ORCH_TOOL_SANDBOX_ENABLED`.

### Example
```python
from src.tool_registry import ToolRegistry, ToolSpec

def echo(message: str) -> str:
    return f"Echo: {message}"

registry = ToolRegistry()
registry.register(ToolSpec(name="echo", description="Echo message", handler=echo))
result = registry.execute("echo", message="hello")
```

## Rule Router (src/router.py)

- `RuleRouter` evaluates deterministic rules in order.
- Each rule returns a tool name + params + reason.
- Defaults to `no_match` when nothing applies.

### Example
```python
from src.router import RuleRouter, Rule

router = RuleRouter()
router.add_rule(
    Rule(
        tool="echo",
        predicate=lambda text: "echo" in text.lower(),
        param_builder=lambda text: {"message": text.replace("echo", "").strip()},
        confidence=0.9,
        reason="keyword_echo",
    )
)

decision = router.route("echo hello")
```

## Where It’s Used

The toy orchestrator now uses both:
- Tool registry for execution
- Rule router for intent

See [examples/toy_orchestrator.py](../examples/toy_orchestrator.py).

## Extension Path

## Policy Router (src/advanced_router.py)

- Policy rules live in `config/router_policy.yaml`.
- Regex-driven matching with explicit confidence + reasons.
- Deterministic and auditable for high-stakes use.

## Extension Path

- Add model selection via `ModelRouter` for cost-aware routing.
- Add async scheduling, cost tracking, and multi-agent planning (out of scope here).

This keeps the core **small, local, and deterministic** while giving teams a clear upgrade path.
