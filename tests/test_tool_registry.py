import os

import pytest

from src.tool_registry import ToolRegistry, ToolSpec


def test_unsafe_tool_without_sandbox_runs_when_not_required(monkeypatch):
    monkeypatch.setenv("ORCH_TOOL_POLICY_ENFORCE", "0")
    monkeypatch.setenv("ORCH_TOOL_SANDBOX_REQUIRED", "1")
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            name="net_call",
            description="unsafe network call",
            handler=lambda query: f"ok:{query}",
            safe=False,
            requires_sandbox=False,
        )
    )

    result = registry.execute("net_call", query="hello")
    assert result["status"] == "ok"
    assert result["result"] == "ok:hello"


def test_unsafe_tool_fallback_unsandboxed(monkeypatch):
    monkeypatch.setenv("ORCH_TOOL_POLICY_ENFORCE", "0")
    monkeypatch.setenv("ORCH_TOOL_SANDBOX_REQUIRED", "0")
    monkeypatch.setenv("ORCH_TOOL_SANDBOX_FALLBACK", "1")

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="unsafe_fallback",
            description="unsafe fallback",
            handler=lambda value: f"ran:{value}",
            safe=False,
            requires_sandbox=True,
            allow_unsandboxed=True,
        )
    )

    result = registry.execute("unsafe_fallback", value="x")
    assert result["status"] == "ok"
    assert result["result"] == "ran:x"


def test_unsafe_tool_requires_sandbox(monkeypatch):
    monkeypatch.setenv("ORCH_TOOL_POLICY_ENFORCE", "0")
    monkeypatch.setenv("ORCH_TOOL_SANDBOX_REQUIRED", "1")
    monkeypatch.setenv("ORCH_TOOL_SANDBOX_ENABLED", "0")

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="unsafe_blocked",
            description="unsafe blocked",
            handler=lambda value: f"ran:{value}",
            safe=False,
            requires_sandbox=True,
        )
    )

    result = registry.execute("unsafe_blocked", value="x")
    assert result["status"] == "error"
    assert result["error"] in {"sandbox_disabled", "sandbox_required", "sandbox_command_missing"}
