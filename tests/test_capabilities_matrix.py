import pytest

from src.orchestrator import Orchestrator
from src.tool_registry import ToolRegistry, ToolSpec


@pytest.mark.parametrize(
    "enabled",
    ["0", "1"],
)
def test_capabilities_matrix_web_search_flag(monkeypatch, enabled):
    monkeypatch.setenv("ORCH_TOOL_WEB_SEARCH_ENABLED", enabled)
    monkeypatch.setenv("ORCH_TOOL_POLICY_ENFORCE", "0")

    orchestrator = Orchestrator()
    tool_names = {tool.name for tool in orchestrator.registry.list_tools()}

    assert ("web_search" in tool_names) is (enabled == "1")
    assert "summarize_text" in tool_names


@pytest.mark.parametrize(
    "expose_decisions,expect_policy_payload",
    [("0", False), ("1", True)],
)
def test_capabilities_matrix_policy_decision_visibility(
    monkeypatch, expose_decisions, expect_policy_payload
):
    monkeypatch.setenv("ORCH_TOOL_POLICY_ENFORCE", "1")
    monkeypatch.setenv("ORCH_POLICY_DECISIONS_IN_RESPONSE", expose_decisions)

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="custom_tool",
            description="custom tool for policy test",
            handler=lambda value: value,
            safe=True,
            requires_sandbox=False,
        )
    )

    result = registry.execute("custom_tool", value="hi")
    assert result["status"] == "error"
    if expect_policy_payload:
        assert "policy_decision" in result
        assert result["policy_decision"]["allowed"] is False
    else:
        assert "policy_decision" not in result


@pytest.mark.parametrize(
    "scrub_enabled,max_chars,expect_redacted,expect_truncated",
    [
        ("1", "8", True, True),
        ("0", "0", False, False),
    ],
)
def test_capabilities_matrix_output_scrub_and_cap(
    monkeypatch, scrub_enabled, max_chars, expect_redacted, expect_truncated
):
    monkeypatch.setenv("ORCH_TOOL_POLICY_ENFORCE", "0")
    monkeypatch.setenv("ORCH_TOOL_OUTPUT_SCRUB_ENABLED", scrub_enabled)
    monkeypatch.setenv("ORCH_TOOL_OUTPUT_MAX_CHARS", max_chars)

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="leaky",
            description="returns a secret token",
            handler=lambda payload: f"token:{payload}",
            safe=True,
            requires_sandbox=False,
        )
    )

    result = registry.execute("leaky", payload="Bearer SECRET_TOKEN_1234567890")
    assert result["status"] == "ok"

    if expect_redacted:
        assert "Bearer" not in result["result"]
    else:
        assert "Bearer" in result["result"]

    if expect_truncated:
        assert result.get("truncated") is True
    else:
        assert "truncated" not in result