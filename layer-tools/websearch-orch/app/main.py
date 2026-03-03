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


def _env_csv_set(name: str, default: str) -> set[str]:
    raw = os.getenv(name, default)
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


UPSTREAM_SEARXNG_URL = os.getenv("UPSTREAM_SEARXNG_URL", "http://127.0.0.1:8888/search")
SEARCH_TOP_N = _env_int("SEARCH_TOP_N", 24)
SEARCH_KEEP_K = _env_int("SEARCH_KEEP_K", 8)
REQUEST_TIMEOUT_SECONDS = _env_int("REQUEST_TIMEOUT_SECONDS", 12)
MAX_RESULTS_PER_DOMAIN = _env_int("MAX_RESULTS_PER_DOMAIN", 2)
MAX_SOURCES_PER_DOMAIN = _env_int("MAX_SOURCES_PER_DOMAIN", 2)
MIN_RESULT_CONTENT_CHARS = _env_int("MIN_RESULT_CONTENT_CHARS", 160)
CITATION_CONTRACT_ENABLED = _env_bool("CITATION_CONTRACT_ENABLED", True)
MIN_GROUNDED_SOURCES = _env_int("MIN_GROUNDED_SOURCES", 2)
SOURCE_TITLE_DEDUP_ENABLED = _env_bool("SOURCE_TITLE_DEDUP_ENABLED", True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
RERANK_ENABLED = _env_bool("RERANK_ENABLED", True)
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
EXTERNAL_WEB_LOADER_MAX_URLS = _env_int("EXTERNAL_WEB_LOADER_MAX_URLS", 10)
EXTERNAL_WEB_LOADER_MAX_BODY_BYTES = _env_int("EXTERNAL_WEB_LOADER_MAX_BODY_BYTES", 200_000)
EXTERNAL_WEB_LOADER_FETCH_TIMEOUT_SECONDS = _env_int("EXTERNAL_WEB_LOADER_FETCH_TIMEOUT_SECONDS", 20)
EXTERNAL_WEB_LOADER_MAX_PAGE_BYTES = _env_int("EXTERNAL_WEB_LOADER_MAX_PAGE_BYTES", 1_500_000)
EXTERNAL_WEB_LOADER_MIN_TEXT_CHARS = _env_int("EXTERNAL_WEB_LOADER_MIN_TEXT_CHARS", 120)
EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS = _env_int("EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS", 2_800)
EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS = _env_int("EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS", 18_000)
EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS = _env_int("EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS", 700)
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
TRUST_POLICY_ENABLED = _env_bool("TRUST_POLICY_ENABLED", True)
TRUST_PRIORITY_DOMAINS = _env_csv_set(
    "TRUST_PRIORITY_DOMAINS",
    "nature.com,pnas.org,science.org,sciencedirect.com,nasa.gov,jpl.nasa.gov,isro.gov.in,esa.int,arxiv.org",
)
TRUST_DEPRIORITIZED_DOMAINS = _env_csv_set(
    "TRUST_DEPRIORITIZED_DOMAINS",
    "medium.com,wikipedia.org,sciencedaily.com,sci.news,universetoday.com",
)
TRUST_DROP_BELOW_SCORE = _env_int("TRUST_DROP_BELOW_SCORE", 0)
QUERY_GUARD_ENABLED = _env_bool("QUERY_GUARD_ENABLED", True)
QUERY_ENTITY_CONFLICT_ACTION = os.getenv("QUERY_ENTITY_CONFLICT_ACTION", "sanitize").strip().lower()
QUERY_ENTITY_CONFLICTS: dict[str, tuple[str, ...]] = {
    "nasa": ("chang'e", "chandrayaan", "kaguya", "selene"),
    "cnsa": ("apollo", "artemis"),
    "isro": ("apollo", "artemis"),
    "jaxa": ("apollo", "artemis", "chang'e"),
    "esa": ("chang'e",),
}
COMPILED_BLOCK_PATTERNS = [re.compile(pat, re.IGNORECASE) for pat in FILTER_BLOCK_PATTERNS]
LXML_DROP_XPATH = (
    "//script|//style|//noscript|//header|//footer|//nav|//aside|//form|"
    "//svg|//canvas|//iframe|//button|//input|//select|//option|"
    "//*[@role='banner']|//*[@role='navigation']|//*[@role='contentinfo']"
)
WHITESPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

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


def _is_placeholder_url(url: str) -> bool:
    host = _domain(url)
    if not host:
        return True
    if host in {"example.com", "example.org", "example.net"}:
        return True
    if "placeholder" in host:
        return True
    if "/example" in url.lower():
        return True
    return False


def _blocked_domain(host: str) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in FILTER_BLOCK_DOMAINS)


def _domain_matches(host: str, domains: set[str]) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def _trust_score_for_domain(host: str) -> int:
    if _domain_matches(host, TRUST_PRIORITY_DOMAINS):
        return 2
    if _domain_matches(host, TRUST_DEPRIORITIZED_DOMAINS):
        return -1
    return 0


def _trust_tier_for_domain(host: str) -> str:
    score = _trust_score_for_domain(host)
    if score >= 2:
        return "priority"
    if score < 0:
        return "deprioritized"
    return "neutral"


def _normalize_query_for_checks(query: str) -> str:
    normalized = query.lower().replace("’", "'")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _query_conflicts(query: str) -> list[tuple[str, str]]:
    normalized = _normalize_query_for_checks(query)
    conflicts: list[tuple[str, str]] = []
    for agency, foreign_tokens in QUERY_ENTITY_CONFLICTS.items():
        if re.search(rf"\b{re.escape(agency)}\b", normalized) is None:
            continue
        for token in foreign_tokens:
            if token in normalized:
                conflicts.append((agency, token))
    return conflicts


def _apply_query_guard(query: str) -> tuple[str, dict[str, Any]]:
    meta: dict[str, Any] = {
        "enabled": QUERY_GUARD_ENABLED,
        "raw_query": query,
        "effective_query": query,
        "action": "pass",
        "conflicts": [],
    }
    if not QUERY_GUARD_ENABLED:
        return query, meta

    conflicts = _query_conflicts(query)
    if not conflicts:
        return query, meta

    meta["conflicts"] = [{"agency": agency, "token": token} for agency, token in conflicts]
    action = QUERY_ENTITY_CONFLICT_ACTION
    if action not in {"sanitize", "reject", "pass"}:
        action = "sanitize"

    if action == "pass":
        meta["action"] = "pass_with_conflicts"
        return query, meta

    if action == "reject":
        meta["action"] = "reject"
        return "", meta

    sanitized = query
    for agency, _token in conflicts:
        sanitized = re.sub(rf"\b{re.escape(agency)}\b", "", sanitized, flags=re.IGNORECASE)
    sanitized = _normalize_whitespace(sanitized)
    if not sanitized:
        meta["action"] = "sanitize_fallback_raw"
        return query, meta

    meta["action"] = "sanitize"
    meta["effective_query"] = sanitized
    return sanitized, meta


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


def _normalized_title_key(text: str) -> str:
    base = NON_ALNUM_RE.sub(" ", text.lower())
    return _normalize_whitespace(base)


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

    return best_text, best_method


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
    page_text_raw, extraction_method = _extract_clean_page_text(url, html_text)
    raw_char_count = len(page_text_raw)
    page_text = _truncate(page_text_raw, EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS)
    doc_char_truncated = len(page_text) < raw_char_count
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)

    return {
        "page_content": page_text,
        "metadata": {
            "source": url,
            "name": url,
            "content_type": content_type,
            "extraction_method": extraction_method,
            "char_count": len(page_text),
            "raw_char_count": raw_char_count,
            "doc_char_truncated": doc_char_truncated,
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
    seen_title_keys: set[str],
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

    if len(content) < MIN_RESULT_CONTENT_CHARS and len(title) < max(20, MIN_RESULT_CONTENT_CHARS // 2):
        return False, "thin_content"

    if _matches_block_pattern(text):
        return False, "blocked_pattern"

    canon = _canonical_url(url)
    if canon in seen_urls:
        return False, "duplicate_url"

    if _is_placeholder_url(url):
        return False, "placeholder_url"

    if SOURCE_TITLE_DEDUP_ENABLED and title:
        title_key = _normalized_title_key(title)
        if title_key and title_key in seen_title_keys:
            return False, "duplicate_title"

    if per_domain[host] >= MAX_RESULTS_PER_DOMAIN:
        return False, "domain_cap"

    if per_domain[host] >= MAX_SOURCES_PER_DOMAIN:
        return False, "source_domain_cap"

    seen_urls.add(canon)
    if SOURCE_TITLE_DEDUP_ENABLED and title:
        title_key = _normalized_title_key(title)
        if title_key:
            seen_title_keys.add(title_key)
    per_domain[host] += 1
    return True, "kept"


def _apply_trust_policy(results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not TRUST_POLICY_ENABLED:
        return results, {"kept": len(results), "trust_drops": 0}

    scored_results: list[tuple[tuple[int, int], dict[str, Any]]] = []
    trust_drops = 0
    placeholder_drops = 0
    tier_counts = {"priority": 0, "neutral": 0, "deprioritized": 0}

    for idx, result in enumerate(results):
        url = str(result.get("url", "")).strip()
        if _is_placeholder_url(url):
            placeholder_drops += 1
            continue
        host = _domain(url)
        trust_score = _trust_score_for_domain(host)
        trust_tier = _trust_tier_for_domain(host)
        if trust_score < TRUST_DROP_BELOW_SCORE:
            trust_drops += 1
            continue

        enriched = dict(result)
        enriched["orch_trust_tier"] = trust_tier
        tier_counts[trust_tier] += 1
        # Preserve rank order inside each trust tier.
        scored_results.append(((trust_score, -idx), enriched))

    scored_results.sort(key=lambda item: item[0], reverse=True)
    final_results = [item[1] for item in scored_results]
    for source_id, item in enumerate(final_results, start=1):
        item["orch_source_id"] = source_id
        item["orch_source_url"] = str(item.get("url", ""))
    summary = {
        "kept": len(final_results),
        "trust_drops": trust_drops,
        "placeholder_drops": placeholder_drops,
        "priority_kept": tier_counts["priority"],
        "neutral_kept": tier_counts["neutral"],
        "deprioritized_kept": tier_counts["deprioritized"],
    }
    return final_results, summary


def _build_citation_contract(results: list[dict[str, Any]]) -> dict[str, Any]:
    mapped: list[dict[str, Any]] = []
    for source in results:
        url = str(source.get("url", "")).strip()
        if not _valid_http_url(url) or _is_placeholder_url(url):
            continue
        mapped.append(
            {
                "source_id": int(source.get("orch_source_id", 0) or 0),
                "title": str(source.get("title", "")).strip(),
                "url": url,
                "domain": _domain(url),
                "trust_tier": str(source.get("orch_trust_tier", "unknown")),
            }
        )

    citation_total = len(mapped)
    citation_status = "disabled"
    if CITATION_CONTRACT_ENABLED:
        citation_status = "ready" if citation_total >= max(1, MIN_GROUNDED_SOURCES) else "insufficient_sources"

    return {
        "enabled": CITATION_CONTRACT_ENABLED,
        "citation_map_status": citation_status,
        "citation_total": citation_total,
        "citation_mapped": citation_total,
        "citation_unmapped": 0,
        "min_grounded_sources": max(1, MIN_GROUNDED_SOURCES),
        "allowed_urls": [item["url"] for item in mapped],
        "sources": mapped,
    }


def _build_grounding_gate(citation_contract: dict[str, Any]) -> dict[str, Any]:
    min_required = int(citation_contract.get("min_grounded_sources", max(1, MIN_GROUNDED_SOURCES)))
    allowed_url_count = len(list(citation_contract.get("allowed_urls", [])))
    grounded_sources = int(citation_contract.get("citation_mapped", 0))
    status = "pass" if allowed_url_count >= min_required else "warn"
    return {
        "status": status,
        "grounded_sources": grounded_sources,
        "min_required": min_required,
        "allowed_url_count": allowed_url_count,
    }


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

        guarded_q, query_guard_meta = _apply_query_guard(q)
        if query_guard_meta.get("action") == "reject":
            self._json(
                {
                    "error": "query_rejected_by_guard",
                    "detail": "query failed entity conflict guard",
                    "query_guard": query_guard_meta,
                },
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        language = query_args.get("language", [None])[0]

        try:
            upstream = _fetch_searx_json(guarded_q, language=language)
        except Exception as exc:  # noqa: BLE001
            log.exception("upstream_fetch_error query=%s guarded_query=%s", q, guarded_q)
            self._json({"error": "upstream_fetch_failed", "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return

        raw_results = list(upstream.get("results", []))
        seen_urls: set[str] = set()
        seen_title_keys: set[str] = set()
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
            keep, reason = _keep_result(item, seen_urls, seen_title_keys, per_domain)
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
                reranked, rerank_scores = _RERANKER.rerank(guarded_q, candidates)
                final_results = reranked[: max(1, RERANK_KEEP_K)]
                rerank_applied = True
            except Exception as exc:  # noqa: BLE001
                # Fail-open: preserve filtered baseline output.
                log.exception("rerank failed query=%r guarded_query=%r (falling back to filtered rank): %s", q, guarded_q, exc)
                final_results = kept[:SEARCH_KEEP_K]

        final_results, trust_summary = _apply_trust_policy(final_results)
        citation_contract = _build_citation_contract(final_results)
        grounding_gate = _build_grounding_gate(citation_contract)
        out["results"] = final_results
        out["query_guard"] = query_guard_meta
        out["grounding"] = {
            "source_count": len(final_results),
            "source_urls": [str(item.get("url", "")) for item in final_results],
            "status": "grounded" if final_results else "ungrounded_fallback",
        }
        out["grounding_gate"] = grounding_gate
        out["trust_summary"] = trust_summary
        out["citation_contract"] = citation_contract
        out["quality_signals"] = {
            "dedupe_drops": reason_counts.get("duplicate_url", 0) + reason_counts.get("duplicate_title", 0),
            "domain_cap_drops": reason_counts.get("domain_cap", 0) + reason_counts.get("source_domain_cap", 0),
            "thin_content_drops": reason_counts.get("thin_content", 0),
            "placeholder_drops": reason_counts.get("placeholder_url", 0) + trust_summary.get("placeholder_drops", 0),
            "unsupported_claim_count": 0,
        }

        log.info(
            "query=%r guarded_query=%r query_action=%s conflicts=%d fetched=%d kept=%d rerank=%s reasons=%s trust=%s citation_map_status=%s citation_mapped=%d citation_unmapped=%d grounding_status=%s grounding_sources=%d grounding_required=%d grounding_allowed_urls=%d dedupe_drops=%d domain_cap_drops=%d unsupported_claim_count=%d top_scores=%s",
            q,
            guarded_q,
            query_guard_meta.get("action"),
            len(query_guard_meta.get("conflicts", [])),
            len(raw_results),
            len(final_results),
            rerank_applied,
            dict(reason_counts),
            trust_summary,
            citation_contract.get("citation_map_status"),
            int(citation_contract.get("citation_mapped", 0)),
            int(citation_contract.get("citation_unmapped", 0)),
            grounding_gate.get("status"),
            int(grounding_gate.get("grounded_sources", 0)),
            int(grounding_gate.get("min_required", 0)),
            int(grounding_gate.get("allowed_url_count", 0)),
            int(out["quality_signals"]["dedupe_drops"]),
            int(out["quality_signals"]["domain_cap_drops"]),
            int(out["quality_signals"]["unsupported_claim_count"]),
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
        input_urls = urls[: max(1, EXTERNAL_WEB_LOADER_MAX_URLS)]
        max_total_chars = (
            EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS
            if EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS > 0
            else None
        )
        remaining_budget = max_total_chars
        total_chars = 0
        total_raw_chars = 0
        doc_char_truncations = 0
        budget_char_truncations = 0
        budget_drops = 0

        for idx, raw_url in enumerate(input_urls):
            url = str(raw_url).strip()
            if not _valid_http_url(url):
                errors[url] = "invalid_url"
                continue
            try:
                doc = _fetch_and_extract_url(url)
                metadata = dict(doc.get("metadata", {}))
                method = str(metadata.get("extraction_method", "unknown"))
                content = str(doc.get("page_content", ""))
                total_raw_chars += int(metadata.get("raw_char_count", len(content)))
                if bool(metadata.get("doc_char_truncated", False)):
                    doc_char_truncations += 1

                budget_char_truncated = False
                if remaining_budget is not None:
                    if remaining_budget <= 0:
                        errors[url] = "text_budget_exhausted"
                        budget_drops += 1
                        continue

                    # Fair-share budget so later sources keep at least a small text slice.
                    pre_budget_chars = len(content)
                    remaining_urls = len(input_urls) - idx - 1
                    reserve_for_tail = max(0, EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS) * max(0, remaining_urls)
                    doc_budget = remaining_budget - reserve_for_tail
                    if doc_budget <= 0:
                        doc_budget = min(remaining_budget, max(0, EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS))
                    doc_budget = max(0, doc_budget)

                    if pre_budget_chars > doc_budget:
                        content = _truncate(content, doc_budget)
                        budget_char_truncated = len(content) < pre_budget_chars
                        if budget_char_truncated:
                            budget_char_truncations += 1
                    remaining_budget -= len(content)
                    metadata["budget_char_limit"] = max_total_chars
                    metadata["budget_remaining_after"] = remaining_budget

                metadata["budget_char_truncated"] = budget_char_truncated
                metadata["char_count"] = len(content)
                doc["page_content"] = content
                doc["metadata"] = metadata
                output_docs.append(doc)
                method_counts[method] += 1
                total_chars += len(content)
            except Exception as exc:  # noqa: BLE001
                errors[url] = str(exc)
                log.warning("web_loader_fetch_error url=%s err=%s", url, exc)

        log.info(
            "web_loader urls=%d ok=%d errors=%d chars=%d raw_chars=%d doc_caps=%d budget_caps=%d budget_drops=%d remaining_budget=%s methods=%s",
            len(urls),
            len(output_docs),
            len(errors),
            total_chars,
            total_raw_chars,
            doc_char_truncations,
            budget_char_truncations,
            budget_drops,
            remaining_budget if remaining_budget is not None else "disabled",
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
