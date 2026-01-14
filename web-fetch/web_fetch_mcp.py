#!/usr/bin/env python3
"""MCP stdio tool: fetch a URL and return cleaned text."""

import os
import re
from typing import Any, Dict, Optional

import httpx
import trafilatura
from readability import Document
from selectolax.parser import HTMLParser
from mcp.server.fastmcp import FastMCP

MCP_SERVER_NAME = "web-fetch"
DEFAULT_TIMEOUT_S = 30
DEFAULT_SEARCH_API_BASE = "http://127.0.0.1:4000/v1/search/searxng-search"

mcp = FastMCP(MCP_SERVER_NAME)


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _text_from_html(html: str) -> str:
    parser = HTMLParser(html)
    for node in parser.css("script,style,noscript,svg,footer,header,nav,aside"):
        node.decompose()
    text = parser.text(separator=" ", strip=True)
    return _collapse_whitespace(text)


def _extract_with_trafilatura(html: str, url: str) -> Optional[Dict[str, Any]]:
    data = trafilatura.bare_extraction(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
        no_fallback=True,
    )
    if data and data.get("text"):
        return data
    return None


def _extract_with_readability(html: str) -> Optional[Dict[str, Any]]:
    doc = Document(html)
    summary_html = doc.summary(html_partial=True)
    text = _text_from_html(summary_html)
    if not text:
        return None
    return {
        "text": text,
        "title": doc.title() or None,
        "author": None,
        "date": None,
        "language": None,
    }


@mcp.tool(name="search.web")
def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web via LiteLLM's /v1/search proxy."""

    api_base = os.getenv("LITELLM_SEARCH_API_BASE", DEFAULT_SEARCH_API_BASE)
    api_key = os.getenv("LITELLM_SEARCH_API_KEY", "dummy")

    payload = {"query": query, "max_results": max_results}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = httpx.post(api_base, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT_S)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"search_failed: {exc}") from exc

    return response.json()


@mcp.tool(name="web.fetch")
def web_fetch(url: str, include_raw_html: bool = False) -> Dict[str, Any]:
    """Fetch a URL and return cleaned text and metadata."""

    user_agent = os.getenv(
        "WEB_FETCH_USER_AGENT",
        "Mozilla/5.0 (compatible; homelab-llm/1.0; +https://localhost)",
    )

    try:
        with httpx.Client(
            headers={"User-Agent": user_agent},
            follow_redirects=True,
            timeout=DEFAULT_TIMEOUT_S,
        ) as client:
            response = client.get(url)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"fetch_failed: {exc}") from exc

    final_url = str(response.url)
    html = response.text

    data = _extract_with_trafilatura(html, final_url)
    if data is None:
        data = _extract_with_readability(html)

    clean_text = ""
    title = None
    byline = None
    published_at = None
    lang = None

    if data:
        clean_text = _collapse_whitespace(data.get("text") or "")
        title = data.get("title") or None
        byline = data.get("author") or None
        published_at = data.get("date") or None
        lang = data.get("language") or None

    if not clean_text:
        clean_text = _text_from_html(html)

    if not clean_text:
        raise RuntimeError("parse_failed: no readable content")

    payload: Dict[str, Any] = {
        "final_url": final_url,
        "title": title,
        "byline": byline,
        "published_at": published_at,
        "lang": lang,
        "clean_text": clean_text,
    }

    if include_raw_html:
        payload["raw_html"] = html

    return payload


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
