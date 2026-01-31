# Routing & Tools

This repo ships a minimal **tool registry**, **rule router**, and an optional **policy router** for production routing.

## Tool Registry (src/tool_registry.py)

- `ToolRegistry` stores `ToolSpec` entries (name, description, handler).
- `execute()` returns a structured result (`status`, `result` or `error`).
- Unsafe tools can be forced through a Docker sandbox via `ORCH_TOOL_SANDBOX_ENABLED`.
- Optional policy enforcement uses `PolicyEngine` with `ORCH_TOOL_POLICY_ENFORCE`.
- Unsafe tools such as `python_eval` and `python_exec` only run in Docker when `ORCH_TOOL_SANDBOX_REQUIRED=1`.

### Example
```python
from src.tool_registry import ToolRegistry, ToolSpec

def echo(message: str) -> str:
    return f"Echo: {message}"

registry = ToolRegistry()
registry.register(ToolSpec(name="echo", description="Echo message", handler=echo))
result = registry.execute("echo", message="hello")
```

## Safe Calculator Tool (src/tools/math.py)

`safe_calc` uses an AST-safe evaluator to avoid `eval()` and prevent code injection. The tool logic is exposed as a standalone module so policy enforcement and tracing can target it directly.

### Entry Points
- `src/tools/math.py` provides `evaluate_expression()` and `SafeMathError`.
- `scripts/safe_calc.py` contains the AST evaluator used by the tool module.
- `src/orchestrator.py` wires `safe_calc` to `evaluate_expression()`.

### Example
```python
from src.tools.math import evaluate_expression

result = evaluate_expression("2 + 2 * (3 - 1)")
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

## Tool Policy Engine (src/policy_engine.py)

- Deterministic allow/deny rules loaded from `config/tool_policy.yaml`.
- Enable enforcement via `ORCH_TOOL_POLICY_ENFORCE=1`.
- Default policy can deny unsafe tools while allowing known safe handlers.
- Policy rules can include conditional checks on tool inputs (length limits).

### Example
```python
from src.policy_engine import PolicyEngine

engine = PolicyEngine.from_env()
decision = engine.check("python_eval", safe=False)
```

### Conditional approvals (length-gated)

You can gate tool access on input size. This is useful for risky tools such as
`python_exec`.

```yaml
- match: "^python_exec$"
    action: allow
    reason: "allow_python_exec_short_input"
    conditions:
        input_param: "code"
        max_input_len: 500
```

If the condition fails, the rule is skipped and the next rule applies (usually
`default_deny`).

## Policy Router (src/advanced_router.py)

- Policy rules live in `config/router_policy.yaml`.
- Regex-driven matching with explicit confidence + reasons.
- Deterministic and auditable for high-stakes use.

## Semantic Router (src/semantic_router.py)

Optional fallback router that uses embeddings to match user intent to tool descriptions **only when deterministic routing fails**.

### Behavior
- Runs after the rule/policy routers return `no_match`.
- Embeds the user input and tool descriptions via Ollama embeddings.
- Routes to the best match if `score >= ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY`.
- Disabled by default for deterministic guarantees.

### Policy Enforcement for Semantic Decisions

Semantic routing only proposes a tool. Actual execution is still governed by
`config/tool_policy.yaml` via `PolicyEngine`. If the policy denies the tool
(for example, `python_exec` is denied by default), the request is blocked even
when a semantic match occurs.

### Flags
- `ORCH_SEMANTIC_ROUTER_ENABLED` (default: `0`)
- `ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY` (default: `0.80`)
- `ORCH_SEMANTIC_ROUTER_EMBED_MODEL` (default: `nomic-embed-text:latest`)
- `ORCH_SEMANTIC_ROUTER_OLLAMA_URL` (default: `http://127.0.0.1:11434`)
- `ORCH_SEMANTIC_ROUTER_TIMEOUT_SEC` (default: `10`)

## Extension Path

- Add model selection via `ModelRouter` for cost-aware routing.
- Add async scheduling, cost tracking, and multi-agent planning (out of scope here).

This keeps the core **small, local, and deterministic** while giving teams a clear upgrade path.
