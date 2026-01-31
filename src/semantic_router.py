from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import requests

from src.router import RouteDecision
from src.tool_registry import ToolSpec


@dataclass
class SemanticMatch:
    tool: str
    score: float


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tool_prompt(tool: ToolSpec) -> str:
    description = (tool.description or "").strip()
    return f"{tool.name}: {description}".strip()


def _embed_with_ollama(text: str, model: str, base_url: str, timeout: float) -> Optional[List[float]]:
    try:
        response = requests.post(
            f"{base_url}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding")
    except Exception:
        return None


class SemanticRouter:
    _MIN_SCORE_GAP = 0.05

    def __init__(
        self,
        tools: Iterable[ToolSpec],
        *,
        enabled: bool,
        min_similarity: float,
        embed_fn: Optional[Callable[[str], Optional[List[float]]]] = None,
    ) -> None:
        self.enabled = enabled
        self.min_similarity = min_similarity
        self._embed_fn = embed_fn
        self._tool_embeddings: Dict[str, List[float]] = {}
        self._tools: Dict[str, ToolSpec] = {tool.name: tool for tool in tools}

    @classmethod
    def from_env(cls, tools: Iterable[ToolSpec]) -> "SemanticRouter":
        enabled = os.getenv("ORCH_SEMANTIC_ROUTER_ENABLED", "0") == "1"
        min_similarity = float(os.getenv("ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY", "0.80"))
        model = os.getenv("ORCH_SEMANTIC_ROUTER_EMBED_MODEL", "nomic-embed-text:latest")
        base_url = os.getenv("ORCH_SEMANTIC_ROUTER_OLLAMA_URL", "http://127.0.0.1:11434")
        timeout = float(os.getenv("ORCH_SEMANTIC_ROUTER_TIMEOUT_SEC", "10"))

        embed_fn = None
        if enabled:
            embed_fn = lambda text: _embed_with_ollama(text, model, base_url, timeout)

        return cls(tools, enabled=enabled, min_similarity=min_similarity, embed_fn=embed_fn)

    def route(self, user_input: str) -> RouteDecision:
        decision, _ = self.route_with_diagnostics(user_input)
        return decision

    def route_with_diagnostics(self, user_input: str) -> tuple[RouteDecision, List[SemanticMatch]]:
        if not self.enabled or not user_input.strip():
            return self._no_match(), []

        if self._embed_fn is None:
            return self._no_match(), []

        input_embedding = self._embed_fn(user_input)
        if not input_embedding:
            return self._no_match(), []

        candidates = self._rank_candidates(input_embedding)
        if not candidates:
            return self._no_match(), []

        best_match = candidates[0]
        runner_up = candidates[1] if len(candidates) > 1 else None
        if best_match.score < self.min_similarity:
            return self._no_match(), candidates

        if runner_up and (best_match.score - runner_up.score) < self._MIN_SCORE_GAP:
            return self._no_match(), candidates

        return (
            RouteDecision(
                tool=best_match.tool,
                params={},
                confidence=best_match.score,
                reason="semantic_match",
            ),
            candidates,
        )

    def _rank_candidates(self, input_embedding: List[float]) -> List[SemanticMatch]:
        candidates: List[SemanticMatch] = []
        for tool in self._tools.values():
            tool_embedding = self._get_tool_embedding(tool)
            if not tool_embedding:
                continue
            score = _cosine_similarity(input_embedding, tool_embedding)
            candidates.append(SemanticMatch(tool=tool.name, score=score))
        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates

    def _get_tool_embedding(self, tool: ToolSpec) -> Optional[List[float]]:
        if tool.name in self._tool_embeddings:
            return self._tool_embeddings[tool.name]

        if self._embed_fn is None:
            return None

        prompt = _tool_prompt(tool)
        embedding = self._embed_fn(prompt)
        if embedding:
            self._tool_embeddings[tool.name] = embedding
        return embedding

    @staticmethod
    def _no_match() -> RouteDecision:
        return RouteDecision(tool=None, params={}, confidence=0.0, reason="no_match")
