from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import os
from typing import Any, Dict, List, Optional

import yaml

from src.tools.orch_tokenizer import orch_tokenizer
from src.tracer import get_tracer

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


def inject_agent_prompt(
    messages: List[Dict[str, Any]],
    agent: AgentProfile,
    trace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    budget_tokens = int(os.getenv("ORCH_MAX_TOKENS", "16384"))
    prompt_tokens = _count_tokens(agent.system_prompt, agent.metadata.get("tokenizer_model", "gpt-aimee"))
    max_prompt_tokens = int(budget_tokens * 0.2) if budget_tokens > 0 else None
    allow_override = bool(agent.metadata.get("allow_overbudget_prompt"))
    override_category = str(agent.metadata.get("prompt_category", "")).lower()
    legal_override = override_category in {"legal", "statute", "legal_statute", "regulatory"}
    if os.getenv("ORCH_AGENT_PROMPT_ALLOW_OVERBUDGET", "0") == "1":
        allow_override = True
    if legal_override:
        allow_override = True

    if max_prompt_tokens is not None and prompt_tokens > max_prompt_tokens:
        _record_prompt_guardrail(
            trace_id,
            agent=agent.name,
            prompt_tokens=prompt_tokens,
            budget_tokens=budget_tokens,
            max_prompt_tokens=max_prompt_tokens,
            override_used=allow_override,
            category=override_category,
        )
        if allow_override:
            logger.warning(
                "Agent prompt exceeds soft-limit; override applied",
                extra={
                    "extra": {
                        "agent": agent.name,
                        "prompt_tokens": prompt_tokens,
                        "budget_tokens": budget_tokens,
                        "max_prompt_tokens": max_prompt_tokens,
                        "override_category": override_category,
                    }
                },
            )
            system_message = {"role": "system", "content": agent.system_prompt}
            return [system_message] + messages if messages else [system_message]
        truncated_prompt = _truncate_to_tokens(
            agent.system_prompt,
            max_prompt_tokens,
            agent.metadata.get("tokenizer_model", "gpt-aimee"),
        )
        if not truncated_prompt:
            logger.warning(
                "Agent prompt injection skipped: token budget exceeded",
                extra={
                    "extra": {
                        "agent": agent.name,
                        "prompt_tokens": prompt_tokens,
                        "budget_tokens": budget_tokens,
                        "max_prompt_tokens": max_prompt_tokens,
                    }
                },
            )
            return messages
        logger.warning(
            "Agent prompt truncated to preserve token budget",
            extra={
                "extra": {
                    "agent": agent.name,
                    "prompt_tokens": prompt_tokens,
                    "budget_tokens": budget_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                }
            },
        )
        system_message = {"role": "system", "content": truncated_prompt}
    else:
        system_message = {"role": "system", "content": agent.system_prompt}
    if not messages:
        return [system_message]
    return [system_message] + messages


def _count_tokens(text: str, model_name: str) -> int:
    if not text:
        return 0
    payload = orch_tokenizer(action="count", text=text, model_name=model_name)
    if payload.get("status") == "ok":
        return int(payload.get("token_count", 0))
    return max(1, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int, model_name: str) -> str:
    if max_tokens <= 0 or not text:
        return ""
    payload = orch_tokenizer(action="encode", text=text, model_name=model_name)
    if payload.get("status") != "ok":
        return ""
    tokens = payload.get("tokens", [])
    truncated = tokens[:max_tokens]
    decoded = orch_tokenizer(action="decode", tokens=truncated, model_name=model_name)
    if decoded.get("status") == "ok":
        return str(decoded.get("text", "")).strip()
    return ""


def _record_prompt_guardrail(
    trace_id: Optional[str],
    agent: str,
    prompt_tokens: int,
    budget_tokens: int,
    max_prompt_tokens: int,
    override_used: bool,
    category: str,
) -> None:
    if not trace_id:
        return
    tracer = get_tracer()
    tracer.record_step(
        trace_id,
        "agent_prompt_guardrail",
        {
            "agent": agent,
            "prompt_tokens": prompt_tokens,
            "budget_tokens": budget_tokens,
            "max_prompt_tokens": max_prompt_tokens,
            "override_used": override_used,
            "override_category": category,
        },
    )
