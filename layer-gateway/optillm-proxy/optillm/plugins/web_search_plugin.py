import json
import os
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import urlopen, Request

SLUG = "web_search"


def _searxng_request(query: str, num_results: int, timeout: int) -> List[Dict[str, str]]:
    base_url = os.environ.get("SEARXNG_API_BASE", "http://127.0.0.1:8888").rstrip("/")
    params = {
        "q": query,
        "format": "json",
        "safesearch": 0,
        "language": "en",
        "categories": "general",
    }
    url = f"{base_url}/search?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "optillm-searxng"})
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    results = []
    for item in data.get("results", [])[:num_results]:
        results.append(
            {
                "title": item.get("title") or "Untitled",
                "url": item.get("url") or "",
                "snippet": item.get("content") or item.get("snippet") or "",
            }
        )
    return results


def extract_search_queries(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return [" ".join(text.split())]


def format_search_results(query: str, results: List[Dict[str, str]]) -> str:
    if not results:
        return f"No search results found for: {query}"
    formatted = f"Search results for '{query}':\n\n"
    for i, result in enumerate(results, 1):
        formatted += f"{i}. **{result['title']}**\n"
        formatted += f"   URL: {result['url']}\n"
        if result.get("snippet"):
            formatted += f"   Summary: {result['snippet']}\n"
        formatted += "\n"
    return formatted


class BrowserSessionManager:
    """
    Minimal session manager for SearXNG-based search.
    Compatible with deep_research session expectations.
    """

    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self._active = True

    def get_or_create_searcher(self):
        return self

    def search(self, query: str, num_results: int = 10, delay_seconds: Optional[int] = None) -> List[Dict[str, str]]:
        if delay_seconds:
            time.sleep(delay_seconds)
        return _searxng_request(query, num_results=num_results, timeout=self.timeout)

    def close(self):
        self._active = False

    def is_active(self) -> bool:
        return self._active


def run(
    system_prompt: str,
    initial_query: str,
    client=None,
    model: str = None,
    request_config: Optional[Dict] = None,
) -> Tuple[str, int]:
    config = request_config or {}
    num_results = config.get("num_results", 10)
    delay_seconds = config.get("delay_seconds", None)
    timeout = config.get("timeout", 30)
    session_manager = config.get("session_manager", None)

    search_queries = extract_search_queries(initial_query)
    if not search_queries:
        return initial_query, 0

    enhanced_query = initial_query
    for query in search_queries:
        if session_manager:
            results = session_manager.search(query, num_results=num_results, delay_seconds=delay_seconds)
        else:
            results = _searxng_request(query, num_results=num_results, timeout=timeout)
        formatted_results = format_search_results(query, results)
        enhanced_query = f"{enhanced_query}\n\n[Web Search Results]:\n{formatted_results}"

    return enhanced_query, 0
