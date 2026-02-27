#!/usr/bin/env python3
"""Local web-search hygiene proxy for Open WebUI.

Responsibilities:
1) Proxy SearXNG JSON search and filter low-signal/junk results.
2) Provide an optional external web-loader endpoint for Open WebUI that fetches
   URL content, cleans noisy HTML boilerplate, and returns compact page text.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import defaultdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import parse, request

try:
    import trafilatura
except Exception:  # noqa: BLE001
    trafilatura = None

try:
    from readability import Document as ReadabilityDocument
except Exception:  # noqa: BLE001
    ReadabilityDocument = None

try:
    from lxml import html as lxml_html
except Exception:  # noqa: BLE001
    lxml_html = None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


UPSTREAM_SEARXNG_URL = os.getenv("UPSTREAM_SEARXNG_URL", "http://127.0.0.1:8888/search")
SEARCH_TOP_N = _env_int("SEARCH_TOP_N", 24)
SEARCH_KEEP_K = _env_int("SEARCH_KEEP_K", 8)
REQUEST_TIMEOUT_SECONDS = _env_int("REQUEST_TIMEOUT_SECONDS", 12)
MAX_RESULTS_PER_DOMAIN = _env_int("MAX_RESULTS_PER_DOMAIN", 2)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
RERANK_ENABLED = _env_bool("RERANK_ENABLED", False)
RERANK_MODEL = os.getenv("RERANK_MODEL", "ms-marco-TinyBERT-L-2-v2")
RERANK_CACHE_DIR = os.getenv("RERANK_CACHE_DIR", "/tmp/websearch-orch-rerank")
RERANK_MAX_DOC_CHARS = _env_int("RERANK_MAX_DOC_CHARS", 1400)
RERANK_TOP_N = _env_int("RERANK_TOP_N", SEARCH_KEEP_K)
RERANK_KEEP_K = _env_int("RERANK_KEEP_K", SEARCH_KEEP_K)
RERANK_MODEL_MAX_LENGTH = _env_int("RERANK_MODEL_MAX_LENGTH", 512)
RERANK_LOG_TOP = _env_int("RERANK_LOG_TOP", 5)

EXTERNAL_WEB_LOADER_ENABLED = _env_bool("EXTERNAL_WEB_LOADER_ENABLED", True)
EXTERNAL_WEB_LOADER_PATH = os.getenv("EXTERNAL_WEB_LOADER_PATH", "/web_loader")
EXTERNAL_WEB_LOADER_API_KEY = os.getenv("EXTERNAL_WEB_LOADER_API_KEY", "")
EXTERNAL_WEB_LOADER_MAX_URLS = _env_int("EXTERNAL_WEB_LOADER_MAX_URLS", 20)
EXTERNAL_WEB_LOADER_MAX_BODY_BYTES = _env_int("EXTERNAL_WEB_LOADER_MAX_BODY_BYTES", 200_000)
EXTERNAL_WEB_LOADER_FETCH_TIMEOUT_SECONDS = _env_int("EXTERNAL_WEB_LOADER_FETCH_TIMEOUT_SECONDS", 20)
EXTERNAL_WEB_LOADER_MAX_PAGE_BYTES = _env_int("EXTERNAL_WEB_LOADER_MAX_PAGE_BYTES", 1_500_000)
EXTERNAL_WEB_LOADER_MIN_TEXT_CHARS = _env_int("EXTERNAL_WEB_LOADER_MIN_TEXT_CHARS", 120)
EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS = _env_int("EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS", 8_000)
EXTERNAL_WEB_LOADER_USER_AGENT = os.getenv(
    "EXTERNAL_WEB_LOADER_USER_AGENT",
    "websearch-orch/1.1 (+https://github.com/open-webui/open-webui)",
)

FILTER_BLOCK_PATTERNS = [
    p.strip()
    for p in os.getenv(
        "FILTER_BLOCK_PATTERNS",
        r"javascript is disabled|captcha|verify you.*robot|invalid parameter|access denied|enable js and disable",
    ).split("|")
    if p.strip()
]
FILTER_BLOCK_DOMAINS = {
    d.strip().lower()
    for d in os.getenv("FILTER_BLOCK_DOMAINS", "facebook.com,tiktok.com,quora.com").split(",")
    if d.strip()
}
COMPILED_BLOCK_PATTERNS = [re.compile(pat, re.IGNORECASE) for pat in FILTER_BLOCK_PATTERNS]
LXML_DROP_XPATH = (
    "//script|//style|//noscript|//header|//footer|//nav|//aside|//form|"
    "//svg|//canvas|//iframe|//button|//input|//select|//option|"
    "//*[@role='banner']|//*[@role='navigation']|//*[@role='contentinfo']"
)
WHITESPACE_RE = re.compile(r"\s+")

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("websearch-orch")
_RERANKER: "LocalReranker | None" = None


def _canonical_url(url: str) -> str:
    parsed = parse.urlparse(url.strip())
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    return parse.urlunparse((parsed.scheme.lower(), host, path, "", "", ""))


def _domain(url: str) -> str:
    return parse.urlparse(url).netloc.lower()


def _blocked_domain(host: str) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in FILTER_BLOCK_DOMAINS)


def _matches_block_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in COMPILED_BLOCK_PATTERNS)


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1]}…"


def _normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def _valid_http_url(url: str) -> bool:
    parsed = parse.urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _decode_html(raw: bytes, content_type: str) -> str:
    match = re.search(r"charset=([^\s;]+)", content_type, flags=re.IGNORECASE)
    charset = match.group(1).strip("\"'") if match else "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except Exception:  # noqa: BLE001
        return raw.decode("utf-8", errors="replace")


def _extract_with_trafilatura(html_text: str, url: str) -> str:
    if trafilatura is None:
        return ""
    try:
        extracted = trafilatura.extract(
            html_text,
            url=url,
            include_links=False,
            include_tables=False,
            include_comments=False,
            deduplicate=True,
        )
    except TypeError:
        extracted = trafilatura.extract(html_text)
    return _normalize_whitespace(extracted or "")


def _extract_with_readability(html_text: str) -> str:
    if ReadabilityDocument is None or lxml_html is None:
        return ""
    summary_html = ReadabilityDocument(html_text).summary(html_partial=True)
    tree = lxml_html.fromstring(summary_html)
    return _normalize_whitespace(tree.text_content() or "")


def _extract_with_lxml(html_text: str) -> str:
    if lxml_html is None:
        return _normalize_whitespace(re.sub(r"<[^>]+>", " ", html_text))

    tree = lxml_html.fromstring(html_text)
    for node in tree.xpath(LXML_DROP_XPATH):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    return _normalize_whitespace(tree.text_content() or "")


def _extract_clean_page_text(url: str, html_text: str) -> tuple[str, str]:
    extraction_chain = (
        ("trafilatura", lambda: _extract_with_trafilatura(html_text, url)),
        ("readability_lxml", lambda: _extract_with_readability(html_text)),
        ("lxml_text_content", lambda: _extract_with_lxml(html_text)),
    )
    best_text = ""
    best_method = "none"

    for method_name, extractor in extraction_chain:
        try:
            candidate = extractor()
        except Exception as exc:  # noqa: BLE001
            log.debug("extractor_failed method=%s url=%s err=%s", method_name, url, exc)
            continue

        if len(candidate) > len(best_text):
            best_text = candidate
            best_method = method_name

        if len(candidate) >= EXTERNAL_WEB_LOADER_MIN_TEXT_CHARS:
            best_text = candidate
            best_method = method_name
            break

    return _truncate(best_text, EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS), best_method


def _fetch_and_extract_url(url: str) -> dict[str, Any]:
    start = time.monotonic()
    req = request.Request(
        url,
        headers={
            "User-Agent": EXTERNAL_WEB_LOADER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    with request.urlopen(req, timeout=EXTERNAL_WEB_LOADER_FETCH_TIMEOUT_SECONDS) as resp:
        content_type = str(resp.headers.get("Content-Type", ""))
        raw = resp.read(max(1, EXTERNAL_WEB_LOADER_MAX_PAGE_BYTES + 1))

    byte_truncated = len(raw) > EXTERNAL_WEB_LOADER_MAX_PAGE_BYTES
    if byte_truncated:
        raw = raw[:EXTERNAL_WEB_LOADER_MAX_PAGE_BYTES]

    html_text = _decode_html(raw, content_type)
    page_text, extraction_method = _extract_clean_page_text(url, html_text)
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)

    return {
        "page_content": page_text,
        "metadata": {
            "source": url,
            "name": url,
            "content_type": content_type,
            "extraction_method": extraction_method,
            "char_count": len(page_text),
            "byte_truncated": byte_truncated,
            "elapsed_ms": elapsed_ms,
        },
    }


def _web_loader_auth_ok(auth_header: str | None) -> bool:
    if not EXTERNAL_WEB_LOADER_API_KEY:
        return True
    if not auth_header:
        return False
    return auth_header.strip() == f"Bearer {EXTERNAL_WEB_LOADER_API_KEY}"


class LocalReranker:
    def __init__(self) -> None:
        from flashrank import Ranker, RerankRequest

        self._Ranker = Ranker
        self._RerankRequest = RerankRequest
        self._ranker = self._Ranker(
            model_name=RERANK_MODEL,
            cache_dir=RERANK_CACHE_DIR,
            max_length=RERANK_MODEL_MAX_LENGTH,
            log_level=LOG_LEVEL,
        )

    def _passage_text(self, result: dict[str, Any]) -> str:
        title = str(result.get("title", "")).strip()
        content = str(result.get("content", "")).strip()
        url = str(result.get("url", "")).strip()
        text = "\n".join(part for part in (title, content, url) if part)
        return _truncate(text, RERANK_MAX_DOC_CHARS)

    def rerank(self, query: str, results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[tuple[str, float]]]:
        passages = [{"id": str(idx), "text": self._passage_text(item)} for idx, item in enumerate(results)]
        request_obj = self._RerankRequest(query=query, passages=passages)
        ranked = self._ranker.rerank(request_obj)

        score_by_id: dict[str, float] = {}
        for item in ranked:
            try:
                score_by_id[str(item["id"])] = float(item["score"])
            except Exception:  # noqa: BLE001
                continue

        enriched: list[dict[str, Any]] = []
        for idx, result in enumerate(results):
            scored = dict(result)
            scored["_rerank_score"] = score_by_id.get(str(idx), float("-inf"))
            enriched.append(scored)

        enriched.sort(key=lambda r: r.get("_rerank_score", float("-inf")), reverse=True)
        score_log = [
            (str(item.get("url", "")), float(item.get("_rerank_score", float("-inf"))))
            for item in enriched[: max(1, RERANK_LOG_TOP)]
        ]
        for item in enriched:
            item.pop("_rerank_score", None)
        return enriched, score_log


def _init_reranker() -> None:
    global _RERANKER  # noqa: PLW0603
    if not RERANK_ENABLED:
        log.info("rerank disabled (RERANK_ENABLED=false)")
        _RERANKER = None
        return

    try:
        _RERANKER = LocalReranker()
        log.info(
            "rerank enabled model=%s top_n=%d keep_k=%d cache_dir=%s",
            RERANK_MODEL,
            RERANK_TOP_N,
            RERANK_KEEP_K,
            RERANK_CACHE_DIR,
        )
    except Exception as exc:  # noqa: BLE001
        _RERANKER = None
        log.exception("rerank init failed (service will fail-open): %s", exc)


def _keep_result(
    result: dict[str, Any],
    seen_urls: set[str],
    per_domain: dict[str, int],
) -> tuple[bool, str]:
    url = str(result.get("url", "")).strip()
    title = str(result.get("title", "")).strip()
    content = str(result.get("content", "")).strip()
    text = f"{title}\n{content}"

    if not url:
        return False, "missing_url"

    parsed = parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, "bad_url"

    host = parsed.netloc.lower()
    if _blocked_domain(host):
        return False, "blocked_domain"

    if not title and not content:
        return False, "empty_text"

    if _matches_block_pattern(text):
        return False, "blocked_pattern"

    canon = _canonical_url(url)
    if canon in seen_urls:
        return False, "duplicate_url"

    if per_domain[host] >= MAX_RESULTS_PER_DOMAIN:
        return False, "domain_cap"

    seen_urls.add(canon)
    per_domain[host] += 1
    return True, "kept"


def _fetch_searx_json(query: str, language: str | None = None) -> dict[str, Any]:
    parsed = parse.urlparse(UPSTREAM_SEARXNG_URL)
    params = dict(parse.parse_qsl(parsed.query, keep_blank_values=True))
    params["q"] = query
    params["format"] = "json"
    if language:
        params["language"] = language
    if SEARCH_TOP_N > 0:
        params["pageno"] = "1"

    upstream_url = parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parse.urlencode(params), parsed.fragment)
    )
    req = request.Request(upstream_url, headers={"Accept": "application/json"})
    with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


class Handler(BaseHTTPRequestHandler):
    server_version = "websearch-orch/1.0"

    def _json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            body_length = int(raw_length)
        except ValueError:
            body_length = 0
        if body_length <= 0:
            raise ValueError("empty_body")
        if body_length > EXTERNAL_WEB_LOADER_MAX_BODY_BYTES:
            raise ValueError("body_too_large")
        payload = self.rfile.read(body_length).decode("utf-8", errors="replace")
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("json_object_required")
        return data

    def do_GET(self) -> None:  # noqa: N802
        parsed = parse.urlparse(self.path)
        path = parsed.path
        query_args = parse.parse_qs(parsed.query)

        if path == "/health":
            self._json(
                {
                    "ok": True,
                    "service": "websearch-orch",
                    "external_web_loader": EXTERNAL_WEB_LOADER_ENABLED,
                }
            )
            return

        if path != "/search":
            self._json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        q = query_args.get("q", [""])[0].strip()
        if not q:
            self._json({"error": "missing_query"}, status=HTTPStatus.BAD_REQUEST)
            return

        language = query_args.get("language", [None])[0]

        try:
            upstream = _fetch_searx_json(q, language=language)
        except Exception as exc:  # noqa: BLE001
            log.exception("upstream_fetch_error query=%s", q)
            self._json({"error": "upstream_fetch_failed", "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return

        raw_results = list(upstream.get("results", []))
        seen_urls: set[str] = set()
        per_domain: dict[str, int] = defaultdict(int)
        kept: list[dict[str, Any]] = []
        reason_counts: dict[str, int] = defaultdict(int)
        target_keep = SEARCH_KEEP_K
        if _RERANKER:
            target_keep = max(SEARCH_KEEP_K, max(1, RERANK_TOP_N))

        for item in raw_results[:SEARCH_TOP_N]:
            if not isinstance(item, dict):
                reason_counts["non_dict_result"] += 1
                continue
            keep, reason = _keep_result(item, seen_urls, per_domain)
            reason_counts[reason] += 1
            if keep:
                kept.append(item)
            if len(kept) >= target_keep:
                break

        out = dict(upstream)
        rerank_applied = False
        rerank_scores: list[tuple[str, float]] = []
        final_results = kept

        if _RERANKER and kept:
            try:
                candidates = kept[: max(1, RERANK_TOP_N)]
                reranked, rerank_scores = _RERANKER.rerank(q, candidates)
                final_results = reranked[: max(1, RERANK_KEEP_K)]
                rerank_applied = True
            except Exception as exc:  # noqa: BLE001
                # Fail-open: preserve filtered baseline output.
                log.exception("rerank failed query=%r (falling back to filtered rank): %s", q, exc)
                final_results = kept[:SEARCH_KEEP_K]

        out["results"] = final_results

        log.info(
            "query=%r fetched=%d kept=%d rerank=%s reasons=%s top_scores=%s",
            q,
            len(raw_results),
            len(final_results),
            rerank_applied,
            dict(reason_counts),
            [(url, round(score, 4)) for url, score in rerank_scores],
        )
        self._json(out)

    def do_POST(self) -> None:  # noqa: N802
        parsed = parse.urlparse(self.path)
        if parsed.path != EXTERNAL_WEB_LOADER_PATH:
            self._json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        if not EXTERNAL_WEB_LOADER_ENABLED:
            self._json({"error": "external_web_loader_disabled"}, status=HTTPStatus.SERVICE_UNAVAILABLE)
            return

        if not _web_loader_auth_ok(self.headers.get("Authorization")):
            self._json({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return

        try:
            payload = self._read_json_body()
        except Exception as exc:  # noqa: BLE001
            self._json({"error": "invalid_json_body", "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        urls = payload.get("urls")
        if not isinstance(urls, list):
            self._json({"error": "urls_must_be_list"}, status=HTTPStatus.BAD_REQUEST)
            return

        output_docs: list[dict[str, Any]] = []
        method_counts: dict[str, int] = defaultdict(int)
        errors: dict[str, str] = {}

        for raw_url in urls[: max(1, EXTERNAL_WEB_LOADER_MAX_URLS)]:
            url = str(raw_url).strip()
            if not _valid_http_url(url):
                errors[url] = "invalid_url"
                continue
            try:
                doc = _fetch_and_extract_url(url)
                output_docs.append(doc)
                method = str(doc.get("metadata", {}).get("extraction_method", "unknown"))
                method_counts[method] += 1
            except Exception as exc:  # noqa: BLE001
                errors[url] = str(exc)
                log.warning("web_loader_fetch_error url=%s err=%s", url, exc)

        total_chars = sum(int(doc.get("metadata", {}).get("char_count", 0)) for doc in output_docs)
        log.info(
            "web_loader urls=%d ok=%d errors=%d chars=%d methods=%s",
            len(urls),
            len(output_docs),
            len(errors),
            total_chars,
            dict(method_counts),
        )
        if errors:
            log.warning("web_loader_errors=%s", errors)

        self._json(output_docs)

    def log_message(self, fmt: str, *args: Any) -> None:
        log.info("%s - %s", self.address_string(), fmt % args)


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = _env_int("PORT", 8899)
    _init_reranker()
    server = ThreadingHTTPServer((host, port), Handler)
    log.info("websearch-orch listening on http://%s:%s", host, port)
    server.serve_forever()


if __name__ == "__main__":
    main()
