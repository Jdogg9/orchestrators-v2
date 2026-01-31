from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import os
import re

from src.policy_engine import PolicyEngine
from src.sandbox import SandboxRunner
from src.tracer import get_tracer


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]
    safe: bool = True
    sandbox_command: Optional[List[str]] = None
    requires_sandbox: bool = True
    allow_unsandboxed: bool = False


class ToolRegistry:
    """Minimal tool registry with bounded execution semantics."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}
        self._sandbox = SandboxRunner()
        self._policy = PolicyEngine.from_env()
        self._output_max_chars = int(os.getenv("ORCH_TOOL_OUTPUT_MAX_CHARS", "4000"))
        self._scrub_enabled = os.getenv("ORCH_TOOL_OUTPUT_SCRUB_ENABLED", "1") == "1"

    def register(self, tool: ToolSpec) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_tools(self) -> List[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def execute(self, name: str, trace_id: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {"status": "error", "error": f"unknown_tool:{name}"}
        decision = self._policy.check(tool.name, tool.safe, params=kwargs)
        if trace_id:
            tracer = get_tracer()
            tracer.record_step(
                trace_id,
                "policy_snapshot",
                {
                    "tool": name,
                    "policy_hash": self._policy.policy_hash,
                    "policy_path": self._policy.policy_path,
                    "policy_enforced": self._policy._enforce,
                    "decision": "allow" if decision.allowed else "deny",
                    "reason": decision.reason,
                    "rule": decision.rule,
                },
            )
        if not decision.allowed:
            response = {
                "status": "error",
                "tool": name,
                "error": f"policy_denied:{decision.reason}",
                "policy_rule": decision.rule,
            }
            if os.getenv("ORCH_POLICY_DECISIONS_IN_RESPONSE", "0") == "1":
                response["policy_decision"] = {
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "rule": decision.rule,
                }
            return response
        try:
            if not tool.safe:
                sandbox_required = tool.requires_sandbox
                enforce_sandbox = os.getenv("ORCH_TOOL_SANDBOX_REQUIRED", "1") == "1"
                allow_fallback = os.getenv("ORCH_TOOL_SANDBOX_FALLBACK", "0") == "1"

                if sandbox_required and enforce_sandbox:
                    if not tool.sandbox_command:
                        return {"status": "error", "tool": name, "error": "sandbox_command_missing"}
                    sandbox_result = self._sandbox.run(tool.sandbox_command, kwargs)
                    if sandbox_result.status != "ok":
                        return {
                            "status": "error",
                            "tool": name,
                            "error": self._scrub_and_cap(sandbox_result.stderr or "sandbox_failed")[0],
                            "exit_code": sandbox_result.exit_code,
                        }
                    result, truncated = self._scrub_and_cap(sandbox_result.stdout)
                    response = {"status": "ok", "tool": name, "result": result}
                    if truncated:
                        response["truncated"] = True
                    return response

                if sandbox_required and not enforce_sandbox:
                    if tool.allow_unsandboxed and allow_fallback:
                        result = tool.handler(**kwargs)
                        formatted, truncated = self._scrub_and_cap_value(result)
                        response = {"status": "ok", "tool": name, "result": formatted}
                        if truncated:
                            response["truncated"] = True
                        return response
                    return {"status": "error", "tool": name, "error": "sandbox_required"}

                result = tool.handler(**kwargs)
                formatted, truncated = self._scrub_and_cap_value(result)
                response = {"status": "ok", "tool": name, "result": formatted}
                if truncated:
                    response["truncated"] = True
                return response

            result = tool.handler(**kwargs)
            formatted, truncated = self._scrub_and_cap_value(result)
            response = {"status": "ok", "tool": name, "result": formatted}
            if truncated:
                response["truncated"] = True
            return response
        except Exception as exc:  # pragma: no cover - defensive
            error_msg, _ = self._scrub_and_cap(str(exc))
            return {"status": "error", "tool": name, "error": error_msg}

    def _scrub_and_cap_value(self, value: Any) -> tuple[Any, bool]:
        if isinstance(value, str):
            return self._scrub_and_cap(value)
        if isinstance(value, (dict, list)):
            scrubbed = self._scrub_container(value)
            return scrubbed, False
        return value, False

    def _scrub_container(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._scrub_container(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._scrub_container(item) for item in value]
        if isinstance(value, str):
            return self._scrub_text(value)
        return value

    def _scrub_and_cap(self, text: str) -> tuple[str, bool]:
        scrubbed = self._scrub_text(text)
        truncated = False
        if self._output_max_chars > 0 and len(scrubbed) > self._output_max_chars:
            scrubbed = scrubbed[: self._output_max_chars].rstrip()
            truncated = True
        return scrubbed, truncated

    def _scrub_text(self, text: str) -> str:
        if not self._scrub_enabled or not text:
            return text
        scrubbed = text
        patterns = [
            r"Bearer\s+[A-Za-z0-9_\-\.]+",
            r"sk-[A-Za-z0-9_\-]{20,}",
            r"ghp_[A-Za-z0-9_\-]{20,}",
            r"-----BEGIN[\sA-Z]+PRIVATE KEY-----",
        ]
        for pattern in patterns:
            scrubbed = re.sub(pattern, "[REDACTED]", scrubbed, flags=re.IGNORECASE)
        scrubbed = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+", " ", scrubbed)
        return scrubbed
