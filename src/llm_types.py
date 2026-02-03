from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    raw: Dict[str, Any]
    provider: str = "unknown"
    latency_ms: Optional[float] = None
    attempts: int = 1
    truncated: bool = False