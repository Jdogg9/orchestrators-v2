from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]
    safe: bool = True


class ToolRegistry:
    """Minimal tool registry with bounded execution semantics."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_tools(self) -> List[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def execute(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {"status": "error", "error": f"unknown_tool:{name}"}
        try:
            result = tool.handler(**kwargs)
            return {"status": "ok", "tool": name, "result": result}
        except Exception as exc:  # pragma: no cover - defensive
            return {"status": "error", "tool": name, "error": str(exc)}
