"""Experimental converter for a tiny CrewAI-style task list."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TaskSpec:
    tool: str
    when: str


def convert_crewai_spec(spec: Dict[str, object]) -> List[TaskSpec]:
    """Convert a minimal CrewAI-like spec to task specs.

    Supported input:
    {
      "tasks": [
        {"tool": "web_search", "when": "contains:news"},
        {"tool": "safe_calc", "when": "contains:calc"}
      ]
    }
    """
    tasks: List[TaskSpec] = []
    if not isinstance(spec, dict):
        return tasks

    raw_tasks = spec.get("tasks", []) or []
    for entry in raw_tasks:
        if not isinstance(entry, dict):
            continue
        tool = entry.get("tool")
        when = entry.get("when") or entry.get("condition")
        if tool and when:
            tasks.append(TaskSpec(tool=str(tool), when=str(when)))
    return tasks
