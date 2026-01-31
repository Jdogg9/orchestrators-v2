from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import os

from src.sandbox import SandboxRunner


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]
    safe: bool = True
    sandbox_command: Optional[List[str]] = None


class ToolRegistry:
    """Minimal tool registry with bounded execution semantics."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}
        self._sandbox = SandboxRunner()

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
            if not tool.safe:
                if os.getenv("ORCH_TOOL_SANDBOX_REQUIRED", "1") == "1":
                    if not tool.sandbox_command:
                        return {"status": "error", "tool": name, "error": "sandbox_command_missing"}
                    sandbox_result = self._sandbox.run(tool.sandbox_command, kwargs)
                    if sandbox_result.status != "ok":
                        return {
                            "status": "error",
                            "tool": name,
                            "error": sandbox_result.stderr or "sandbox_failed",
                            "exit_code": sandbox_result.exit_code,
                        }
                    return {"status": "ok", "tool": name, "result": sandbox_result.stdout}
                return {"status": "error", "tool": name, "error": "sandbox_required"}

            result = tool.handler(**kwargs)
            return {"status": "ok", "tool": name, "result": result}
        except Exception as exc:  # pragma: no cover - defensive
            return {"status": "error", "tool": name, "error": str(exc)}
