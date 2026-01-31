from orchestrators_v2.interop.langgraph import convert_graph, to_rule_router_snippet


def test_convert_graph_trivial():
    graph = {
        "nodes": [{"id": "echo"}, {"id": "safe_calc"}],
        "edges": [{"from": "echo", "to": "safe_calc", "when": "contains:calc"}],
    }

    rules = convert_graph(graph)
    assert len(rules) == 1
    assert rules[0].tool == "safe_calc"
    assert rules[0].match == "contains:calc"

    snippet = to_rule_router_snippet(rules)
    assert "RuleRouter" in snippet
    assert "safe_calc" in snippet
