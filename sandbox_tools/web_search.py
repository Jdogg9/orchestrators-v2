from __future__ import annotations

import json
import re
import sys
from html import unescape
from typing import Any, Dict, List
from urllib.parse import quote
from urllib.request import Request, urlopen

DUCKDUCKGO_HTML = "https://duckduckgo.com/html/?q="


def _load_payload() -> Dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _fetch_html(query: str) -> str:
    url = f"{DUCKDUCKGO_HTML}{quote(query)}"
    req = Request(url, headers={"User-Agent": "orchestrators-v2-sandbox"})
    with urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _parse_results(html: str, max_results: int, snippet_max_chars: int) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>', re.IGNORECASE)
    snippet_pattern = re.compile(r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>', re.IGNORECASE)
    snippets = [unescape(re.sub(r"<.*?>", "", s.group("snippet"))) for s in snippet_pattern.finditer(html)]

    for idx, match in enumerate(pattern.finditer(html)):
        if len(results) >= max_results:
            break
        title = unescape(re.sub(r"<.*?>", "", match.group("title")))
        url = unescape(match.group("url"))
        snippet = snippets[idx] if idx < len(snippets) else ""
        if len(snippet) > snippet_max_chars:
            snippet = snippet[:snippet_max_chars].rstrip()
        results.append({"title": title, "url": url, "snippet": snippet})
    return results


def main() -> int:
    payload = _load_payload()
    query = str(payload.get("query", "") or "").strip()
    max_results = int(payload.get("max_results", 5) or 5)
    snippet_max_chars = int(payload.get("snippet_max_chars", 400) or 400)

    if not query:
        print(json.dumps({"status": "error", "error": "query_required"}))
        return 2
    if max_results <= 0:
        print(json.dumps({"status": "error", "error": "max_results_invalid"}))
        return 2

    try:
        html = _fetch_html(query)
        results = _parse_results(html, max_results, snippet_max_chars)
        print(json.dumps({"status": "ok", "results": results}))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
