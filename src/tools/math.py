"""AST-safe math evaluator tool."""
from __future__ import annotations

from scripts.safe_calc import safe_eval, SafeCalcError


class SafeMathError(ValueError):
    """Raised for invalid or unsupported math expressions."""


def evaluate_expression(expression: str) -> float:
    """Evaluate a math expression using the AST-safe evaluator."""
    try:
        return safe_eval(expression)
    except SafeCalcError as exc:
        raise SafeMathError(str(exc)) from exc
