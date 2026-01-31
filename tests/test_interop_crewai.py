from orchestrators_v2.interop.crewai import TaskSpec, convert_crewai_spec


def test_convert_crewai_spec():
    spec = {
        "tasks": [
            {"tool": "web_search", "when": "contains:news"},
            {"tool": "safe_calc", "when": "contains:calc"},
        ]
    }

    tasks = convert_crewai_spec(spec)
    assert tasks == [
        TaskSpec(tool="web_search", when="contains:news"),
        TaskSpec(tool="safe_calc", when="contains:calc"),
    ]
