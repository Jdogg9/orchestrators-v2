from __future__ import annotations

from typing import List, Dict, Any


def web_search(query: str, max_results: int = 5, snippet_max_chars: int = 400) -> List[Dict[str, Any]]:
    """Simple DuckDuckGo search wrapper (optional dependency)."""
    query = (query or "").strip()
    if not query:
        raise ValueError("query is required")
    if max_results <= 0:
        raise ValueError("max_results must be > 0")
    if snippet_max_chars <= 0:
        raise ValueError("snippet_max_chars must be > 0")

    try:
        from duckduckgo_search import DDGS
    except ImportError as exc:
        raise RuntimeError("dependency_missing:duckduckgo-search") from exc

    results: List[Dict[str, Any]] = []
    with DDGS() as ddgs:
        for row in ddgs.text(query, max_results=max_results):
            snippet = row.get("body") or ""
            if len(snippet) > snippet_max_chars:
                snippet = snippet[:snippet_max_chars].rstrip()
            results.append({
                "title": row.get("title"),
                "url": row.get("href"),
                "snippet": snippet,
            })
    return results
