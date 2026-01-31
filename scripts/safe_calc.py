#!/usr/bin/env python3
"""AST-based safe calculator.

Usage:
  ./scripts/safe_calc.py "2 + 2 * (3 - 1)"
  echo "10/4" | ./scripts/safe_calc.py

Outputs JSON:
  {"status":"ok","result":5.0}
"""
from __future__ import annotations

import ast
import json
import operator
import sys
from typing import Any

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class SafeCalcError(ValueError):
    pass


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return float(OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right)))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return float(OPS[type(node.op)](_eval_node(node.operand)))
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    raise SafeCalcError("unsupported_expression")


def safe_eval(expr: str) -> float:
    if not expr or not expr.strip():
        raise SafeCalcError("missing_expression")
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)


def _read_expression(argv: list[str]) -> str:
    if len(argv) > 1:
        return " ".join(argv[1:]).strip()
    return sys.stdin.read().strip()


def main() -> int:
    expr = _read_expression(sys.argv)
    try:
        result = safe_eval(expr)
        print(json.dumps({"status": "ok", "result": result}))
        return 0
    except SafeCalcError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    except Exception:
        print(json.dumps({"status": "error", "error": "invalid_expression"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
