import pytest

from src.orchestrator import Orchestrator
from src.tool_registry import ToolRegistry, ToolSpec
from src.tools.orch_tokenizer import orch_tokenizer


def test_orch_tokenizer_registered():
    orchestrator = Orchestrator()
    tool_names = {tool.name for tool in orchestrator.registry.list_tools()}
    assert "orch_tokenizer" in tool_names


def test_orch_tokenizer_encode_decode_roundtrip():
    encoded = orch_tokenizer(action="encode", text="Hello")
    assert encoded["status"] == "ok"
    assert encoded["token_count"] > 0
    tokens = encoded.get("tokens")
    assert isinstance(tokens, list) and tokens

    decoded = orch_tokenizer(action="decode", tokens=tokens)
    assert decoded["status"] == "ok"
    assert decoded["text"] == "Hello"


def test_orch_tokenizer_count_only():
    result = orch_tokenizer(action="count", text="Hello world")
    assert result["status"] == "ok"
    assert result["token_count"] > 0
    assert "tokens" not in result


def test_orch_tokenizer_invalid_action():
    result = orch_tokenizer(action="bad_action", text="Hello")
    assert result["status"] == "error"
    assert result["error"] == "invalid_action"


def test_orch_tokenizer_missing_inputs():
    result = orch_tokenizer(action="encode", text="")
    assert result["status"] == "error"
    assert result["error"] == "missing_text"

    result = orch_tokenizer(action="decode", tokens=None)
    assert result["status"] == "error"
    assert result["error"] == "missing_tokens"


def test_orch_tokenizer_via_registry():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="orch_tokenizer",
            description="Tokenizer tool",
            handler=orch_tokenizer,
            safe=True,
            requires_sandbox=False,
        )
    )

    result = registry.execute("orch_tokenizer", action="count", text="Hello")
    assert result["status"] == "ok"
    assert result["result"]["token_count"] > 0
