from __future__ import annotations

import re
from typing import Dict, Set


def summary_quality_metrics(original: str, summary: str) -> Dict[str, float]:
    if not original or not original.strip():
        raise ValueError("original is required")
    if not summary or not summary.strip():
        raise ValueError("summary is required")

    original_clean = _normalize_text(original)
    summary_clean = _normalize_text(summary)

    original_keywords = _extract_keywords(original_clean)
    summary_keywords = _extract_keywords(summary_clean)

    if not original_keywords:
        keyword_coverage = 1.0
    else:
        keyword_coverage = len(original_keywords & summary_keywords) / len(original_keywords)

    compression_ratio = len(summary_clean) / max(len(original_clean), 1)
    sentence_capture = _sentence_capture_ratio(original_clean, summary_clean)

    return {
        "keyword_coverage": round(keyword_coverage, 4),
        "compression_ratio": round(compression_ratio, 4),
        "sentence_capture_ratio": round(sentence_capture, 4),
    }


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _extract_keywords(text: str) -> Set[str]:
    tokens = re.findall(r"[A-Za-z0-9']+", text.lower())
    return {token for token in tokens if len(token) >= 4}


def _sentence_capture_ratio(original: str, summary: str) -> float:
    original_sentences = [s.strip() for s in re.split(r"[.!?]+", original) if s.strip()]
    if not original_sentences:
        return 1.0
    captured = 0
    summary_lower = summary.lower()
    for sentence in original_sentences:
        snippet = sentence[:60].lower()
        if snippet and snippet in summary_lower:
            captured += 1
    return captured / len(original_sentences)
