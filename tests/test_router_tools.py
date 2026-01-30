from src.router import RuleRouter, Rule
from src.tool_registry import ToolRegistry, ToolSpec


def test_rule_router_selects_first_match():
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
    assert decision.tool == "echo"
    assert decision.params["message"] == "hello"
    assert decision.reason == "keyword_echo"


def test_tool_registry_execute():
    registry = ToolRegistry()

    def echo(message: str) -> str:
        return f"Echo: {message}"

    registry.register(ToolSpec(name="echo", description="Echo", handler=echo))

    result = registry.execute("echo", message="hi")
    assert result["status"] == "ok"
    assert result["result"] == "Echo: hi"

    missing = registry.execute("missing")
    assert missing["status"] == "error"
