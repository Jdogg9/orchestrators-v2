from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import os
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger("orchestrators_v2.agents")


@dataclass(frozen=True)
class AgentProfile:
    name: str
    description: str
    system_prompt: str
    tools: List[str]
    metadata: Dict[str, Any]


def _agent_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    default_dir = root / "config" / "agents"
    return Path(os.getenv("ORCH_AGENT_DIR", str(default_dir)))


def _load_agent_file(path: Path) -> Optional[AgentProfile]:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load agent config", extra={"extra": {"path": str(path), "error": str(exc)}})
        return None

    name = str(data.get("name", "")).strip()
    system_prompt = str(data.get("system_prompt", "")).strip()
    if not name or not system_prompt:
        return None

    return AgentProfile(
        name=name,
        description=str(data.get("description", "")),
        system_prompt=system_prompt,
        tools=list(data.get("tools", []) or []),
        metadata=dict(data.get("metadata", {}) or {}),
    )


def list_agents() -> List[Dict[str, Any]]:
    agents = []
    agent_dir = _agent_dir()
    if not agent_dir.exists():
        return agents

    for path in sorted(agent_dir.glob("*.y*ml")):
        agent = _load_agent_file(path)
        if not agent:
            continue
        agents.append({
            "name": agent.name,
            "description": agent.description,
            "tools": agent.tools,
            "metadata": agent.metadata,
        })
    return agents


def get_agent(name: str) -> Optional[AgentProfile]:
    agent_dir = _agent_dir()
    if not agent_dir.exists():
        return None

    for path in agent_dir.glob("*.y*ml"):
        agent = _load_agent_file(path)
        if agent and agent.name.lower() == name.lower():
            return agent
    return None


def inject_agent_prompt(messages: List[Dict[str, Any]], agent: AgentProfile) -> List[Dict[str, Any]]:
    system_message = {"role": "system", "content": agent.system_prompt}
    if not messages:
        return [system_message]
    return [system_message] + messages
