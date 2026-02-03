# Routing & Tools

This repo ships a minimal **tool registry**, **rule router**, and an optional **policy router** for production routing.

## Tool Registry (src/tool_registry.py)

- `ToolRegistry` stores `ToolSpec` entries (name, description, handler).
- `execute()` returns a structured result (`status`, `result` or `error`).
- Unsafe tools can be forced through a Docker sandbox via `ORCH_TOOL_SANDBOX_ENABLED`.
- Optional policy enforcement uses `PolicyEngine` with `ORCH_TOOL_POLICY_ENFORCE`.
- Unsafe tools such as `python_eval` and `python_exec` only run in Docker when `ORCH_TOOL_SANDBOX_REQUIRED=1`.
- `ORCH_TOOL_SANDBOX_FALLBACK=1` allows per-tool unsandboxed fallbacks when explicitly configured.

### Example
```python
from src.tool_registry import ToolRegistry, ToolSpec

def echo(message: str) -> str:
    return f"Echo: {message}"

registry = ToolRegistry()
registry.register(ToolSpec(name="echo", description="Echo message", handler=echo))
result = registry.execute("echo", message="hello")
```

## Built-in Tools (Default)

| Tool | Safe | Sandbox | Notes |
| --- | --- | --- | --- |
| `echo` | ✅ | No | Echo input |
| `safe_calc` | ✅ | No | AST-safe math |
| `summarize_text` | ✅ | No | Extractive summary (no LLM) |
| `python_eval` | ❌ | Required | Requires Docker sandbox |
| `python_exec` | ❌ | Required | Requires Docker sandbox |

## Optional Tools (Off by Default)

| Tool | Flag | Safety | Notes |
| --- | --- | --- | --- |
| `web_search` | `ORCH_TOOL_WEB_SEARCH_ENABLED=1` | ❌ | Uses DuckDuckGo, gated by policy rules |

## Safe Extension Pattern

```python
from src.tool_registry import ToolRegistry, ToolSpec

def redact(text: str) -> str:
    return text.replace("secret", "[REDACTED]")

registry = ToolRegistry()
registry.register(
    ToolSpec(
        name="redact_text",
        description="Redact secrets from text",
        handler=redact,
        safe=True,
    )
)
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

See also: [Tool Approval Contract](TOOL_APPROVAL_CONTRACT.md) and [Trust Panel](TRUST_PANEL.md).

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

## Tiered Reasoning Strategy (Token-Aware)

Orchestrators-v2 uses **token-density** to select the best model tier and to trigger
summary mode when the context grows too large. The tiers are documented and enforced
through environment-driven thresholds:

| Tier | Token Budget | Routing Behavior | Example Models |
| --- | --- | --- | --- |
| Tier 1 (Fast-Path) | < 4k tokens | Routes to efficient local SLMs | Phi-4, Llama-3-8B |
| Tier 2 (Reasoning) | 4k–32k tokens | Routes to frontier local models | Llama-3-70B |
| Tier 3 (Large Context) | > 32k tokens | Triggers summary mode before routing | Llama-3-70B + Summary |

**Deterministic standard (2026 baseline):** 4k (Tier 1), 32k (Tier 2 ceiling), 32k+ (Tier 3).

### Configuration

- `ORCH_MODEL_CHAT_TIER1_MAX_TOKENS` (default: `4096`)
- `ORCH_MODEL_REASONER_TIER1_MAX_TOKENS` (default: `32768`)
- `ORCH_TIER3_MIN_TOKENS` (default: `32768`)
- `ORCH_MAX_TOKENS` (default: `16384`)
- `ORCH_TOKEN_BUDGET_SUMMARY_ENABLED` (default: `0`, Tier-3 forces summary)

### Summary Mode Behavior

When Tier 3 is reached, the orchestrator inserts a pinned system summary message:

```
Previous Context Summary: <summary content>
```

This preserves the **initial goal** and pinned context while trimming the middle
conversation turns.

### Why This Upgrade Matters

Token-aware routing prevents **semantic drift** by keeping the initial intent pinned
and trimming only the noisy middle turns. The result is a deterministic, auditable
context policy that preserves reasoning density as conversations grow.

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
