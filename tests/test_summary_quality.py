import pytest

from src.tools.summarize import summarize_text
from src.tools.summary_quality import summary_quality_metrics
from src.orchestrator import Orchestrator


def test_summary_quality_metrics_basic():
    original = (
        "The pipeline extracts signals from user requests. "
        "Token-aware pruning protects intent integrity during overflow. "
        "Summary mode preserves high-value context for downstream agents."
    )
    summary = summarize_text(original, max_sentences=2)["summary"]
    metrics = summary_quality_metrics(original, summary)

    assert 0 <= metrics["keyword_coverage"] <= 1
    assert 0 < metrics["compression_ratio"] < 1
    assert metrics["sentence_capture_ratio"] >= 0.33


def test_summary_quality_metrics_full_coverage_when_same():
    original = "Summary quality should remain perfect when text is unchanged."
    metrics = summary_quality_metrics(original, original)

    assert metrics["keyword_coverage"] == 1.0
    assert metrics["compression_ratio"] == 1.0
    assert metrics["sentence_capture_ratio"] == 1.0


def test_summary_quality_metrics_rejects_empty():
    with pytest.raises(ValueError):
        summary_quality_metrics("", "summary")
    with pytest.raises(ValueError):
        summary_quality_metrics("original", "")


def test_summary_context_preservation_for_pinned_keywords():
    orchestrator = Orchestrator()
    pinned_keywords = ["SOVEREIGN", "NON-DETERMINISTIC", "TOKEN BUDGET"]
    removed_messages = [
        {
            "role": "user",
            "content": (
                "Pinned directive: SOVEREIGN safety is mandatory. "
                "We must avoid NON-DETERMINISTIC behavior at all costs. "
                "TOKEN BUDGET compliance is required across every request."
            ),
        },
        {
            "role": "assistant",
            "content": "Acknowledged. We will preserve the directive in future summaries.",
        },
    ]

    summary_message = orchestrator._summarize_removed(removed_messages)
    for keyword in pinned_keywords:
        assert keyword in summary_message
