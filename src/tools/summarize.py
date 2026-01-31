from __future__ import annotations

from typing import Dict


def summarize_text(text: str, max_sentences: int = 3) -> Dict[str, str]:
    """Lightweight extractive summary (no LLM)."""
    if not text or not text.strip():
        raise ValueError("text is required")
    if max_sentences <= 0:
        raise ValueError("max_sentences must be > 0")

    normalized = " ".join(text.strip().split())
    sentences = [s.strip() for s in normalized.split(".") if s.strip()]
    summary = ". ".join(sentences[:max_sentences])
    if summary and not summary.endswith("."):
        summary += "."
    return {
        "summary": summary,
        "sentences": str(min(len(sentences), max_sentences)),
    }
