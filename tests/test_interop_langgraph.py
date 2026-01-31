from orchestrators_v2.interop.langgraph import RuleSpec, convert_graph, convert_langgraph_spec, to_rule_router_snippet


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


def test_convert_langgraph_spec_edges():
    payload = {
        "edges": [
            {"from": "router", "to": "echo", "when": "contains:echo"},
            {"from": "router", "to": "safe_calc", "condition": "contains:calc"},
        ]
    }

    rules = convert_langgraph_spec(payload)
    assert rules == [
        RuleSpec(tool="echo", match="contains:echo"),
        RuleSpec(tool="safe_calc", match="contains:calc"),
    ]
