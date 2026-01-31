from src.semantic_router import SemanticRouter
from src.tool_registry import ToolSpec


def test_semantic_router_matches_best_tool():
    tools = [
        ToolSpec(name="safe_calc", description="Evaluate arithmetic expressions", handler=lambda **_: None),
        ToolSpec(name="python_eval", description="Execute python code", handler=lambda **_: None),
    ]

    def embed_fn(text: str):
        if "safe_calc" in text or "arithmetic" in text:
            return [1.0, 0.0]
        if "python_eval" in text or "python" in text:
            return [0.0, 1.0]
        if "calculate" in text:
            return [0.9, 0.1]
        return [0.0, 0.0]

    router = SemanticRouter(tools, enabled=True, min_similarity=0.8, embed_fn=embed_fn)
    decision = router.route("calculate 2 + 2")

    assert decision.tool == "safe_calc"
    assert decision.reason == "semantic_match"
    assert decision.confidence >= 0.8


def test_semantic_router_respects_threshold():
    tools = [
        ToolSpec(name="safe_calc", description="Evaluate arithmetic expressions", handler=lambda **_: None),
    ]

    def embed_fn(text: str):
        if "safe_calc" in text or "arithmetic" in text:
            return [1.0, 0.0]
        return [0.2, 0.1]

    router = SemanticRouter(tools, enabled=True, min_similarity=0.99, embed_fn=embed_fn)
    decision = router.route("calculate 2 + 2")

    assert decision.tool is None
    assert decision.reason == "no_match"


def test_semantic_router_disabled_returns_no_match():
    tools = [
        ToolSpec(name="safe_calc", description="Evaluate arithmetic expressions", handler=lambda **_: None),
    ]

    router = SemanticRouter(tools, enabled=False, min_similarity=0.8, embed_fn=lambda _: [1.0, 0.0])
    decision = router.route("calculate 2 + 2")

    assert decision.tool is None
    assert decision.reason == "no_match"


def test_semantic_router_avoids_ambiguous_match():
    tools = [
        ToolSpec(name="safe_calc", description="Evaluate arithmetic expressions", handler=lambda **_: None),
        ToolSpec(name="python_exec", description="Execute python code", handler=lambda **_: None),
    ]

    def embed_fn(text: str):
        if "safe_calc" in text:
            return [1.0, 0.0]
        if "python_exec" in text:
            return [1.0, 0.0]
        return [1.0, 0.0]

    router = SemanticRouter(tools, enabled=True, min_similarity=0.8, embed_fn=embed_fn)
    decision = router.route("do the thing")

    assert decision.tool is None
    assert decision.reason == "no_match"


def test_semantic_router_rejects_low_confidence_match():
    tools = [
        ToolSpec(name="safe_calc", description="Evaluate arithmetic expressions", handler=lambda **_: None),
        ToolSpec(name="python_eval", description="Execute python code", handler=lambda **_: None),
    ]

    def embed_fn(text: str):
        if "safe_calc" in text:
            return [1.0, 0.0]
        if "python_eval" in text:
            return [0.0, 1.0]
        return [0.65, 0.35]

    router = SemanticRouter(tools, enabled=True, min_similarity=0.9, embed_fn=embed_fn)
    decision = router.route("maybe run something")

    assert decision.tool is None
    assert decision.reason == "no_match"
