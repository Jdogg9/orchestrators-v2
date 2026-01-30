# Safe Calculator (AST-Based)

The toy orchestrator uses `eval()` on purpose to keep the example small. **Do not reuse it in production.**

This doc shows a safer alternative using Python’s `ast` module to evaluate basic math expressions.

## Goals
- Allow only arithmetic: `+`, `-`, `*`, `/`, parentheses, and numbers.
- Reject names, attribute access, function calls, and other unsafe nodes.

## Minimal Implementation

```python
import ast
import operator

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node):
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    raise ValueError("Unsupported expression")
```

## Integration Idea (Toy Orchestrator)
Replace the `eval()` call in `examples/toy_orchestrator.py` with `safe_eval()` and keep the warning banner to reinforce the lesson.

## Why This Matters
- **Prevents code execution** (no names, calls, or attributes).
- **Limits surface area** to math expressions only.
- **Matches the repo philosophy**: bounded, receipted, and default-off.
