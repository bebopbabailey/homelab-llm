#!/usr/bin/env python3
"""MCP stdio tool: fetch bounded public-web content and normalize search results."""

from __future__ import annotations

import atexit
import hashlib
import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
import trafilatura
from mcp.server.fastmcp import FastMCP
from readability import Document
from selectolax.parser import HTMLParser

MCP_SERVER_NAME = "web-fetch"
DEFAULT_SEARCH_API_BASE = "http://127.0.0.1:4000/v1/search/searxng-search"
DEFAULT_USER_AGENT = "homelab-llm-web-fetch/1.0"
DEFAULT_ACCEPT = "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1"
ALLOWED_MEDIA_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")

mcp = FastMCP(MCP_SERVER_NAME)

_HTTP_CLIENT: httpx.Client | None = None
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
URL_RE = re.compile(r"https?://[^\s)>\"]+")


class ToolContractError(RuntimeError):
    """Stable tool error with a machine-parseable code prefix."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    http_status: int
    content_type: str
    body_bytes: bytes
    encoding: str


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _fetch_max_bytes() -> int:
    return _env_int("WEB_FETCH_MAX_BYTES", 2_097_152)


def _fetch_max_clean_text_chars() -> int:
    return _env_int("WEB_FETCH_MAX_CLEAN_TEXT_CHARS", 50_000)


def _fetch_max_raw_html_chars() -> int:
    return _env_int("WEB_FETCH_MAX_RAW_HTML_CHARS", 200_000)


def _fetch_max_redirects() -> int:
    return _env_int("WEB_FETCH_MAX_REDIRECTS", 5)


def _fetch_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=float(_env_int("WEB_FETCH_CONNECT_TIMEOUT", 5)),
        read=float(_env_int("WEB_FETCH_READ_TIMEOUT", 20)),
        write=float(_env_int("WEB_FETCH_WRITE_TIMEOUT", 5)),
        pool=float(_env_int("WEB_FETCH_POOL_TIMEOUT", 5)),
    )


def _fetch_limits() -> httpx.Limits:
    return httpx.Limits(
        max_connections=_env_int("WEB_FETCH_MAX_CONNECTIONS", 10),
        max_keepalive_connections=_env_int("WEB_FETCH_MAX_KEEPALIVE_CONNECTIONS", 5),
        keepalive_expiry=float(_env_int("WEB_FETCH_KEEPALIVE_EXPIRY", 15)),
    )


def _build_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": os.getenv("WEB_FETCH_USER_AGENT", DEFAULT_USER_AGENT)},
        follow_redirects=False,
        limits=_fetch_limits(),
        timeout=_fetch_timeout(),
        trust_env=False,
        verify=True,
    )


def _get_client() -> httpx.Client:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = _build_client()
    return _HTTP_CLIENT


def _close_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None:
        _HTTP_CLIENT.close()
        _HTTP_CLIENT = None


atexit.register(_close_client)


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _coerce_string(value: Any) -> str:
    if value is None:
        return ""
    return _collapse_whitespace(str(value))


def _normalize_optional_string(value: Any) -> str | None:
    text = _coerce_string(value)
    return text or None


def _clip_text(value: str, limit: int) -> str:
    return value[:limit].strip()


def _strip_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def _split_url(url: str, error_code: str) -> Any:
    candidate = _strip_fragment(url.strip())
    try:
        parts = urlsplit(candidate)
    except ValueError as exc:
        raise ToolContractError(error_code, f"invalid URL parse: {exc.__class__.__name__}") from exc

    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ToolContractError(error_code, "only absolute http(s) URLs with a host are allowed")
    if parts.username or parts.password:
        raise ToolContractError(error_code, "credentials in URL are not allowed")
    return parts


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
        or (isinstance(ip, ipaddress.IPv4Address) and ip in CGNAT_NETWORK)
    )


def _resolve_host_ips(hostname: str, port: int) -> list[ipaddress._BaseAddress]:
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None

    if literal is not None:
        return [literal]

    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ToolContractError("upstream_failure", f"{exc.__class__.__name__}: {exc}") from exc

    ips: list[ipaddress._BaseAddress] = []
    for record in records:
        address = record[4][0]
        try:
            ips.append(ipaddress.ip_address(address))
        except ValueError:
            continue
    if not ips:
        raise ToolContractError("upstream_failure", "name resolution returned no usable IPs")
    return ips


def _validate_public_target(url: str, blocked_code: str) -> str:
    parts = _split_url(url, blocked_code)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    for ip in _resolve_host_ips(parts.hostname, port):
        if _is_blocked_ip(ip):
            raise ToolContractError(blocked_code, f"resolved target blocked: {ip}")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def _parse_media_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    media_type = content_type.split(";", 1)[0].strip().lower()
    if not media_type or "/" not in media_type:
        return None
    return media_type


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
    normalized = _normalize_extracted_data(data)
    if normalized and normalized.get("text"):
        return normalized
    return None


def _extract_markdown_with_trafilatura(html: str, url: str) -> str | None:
    markdown = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_comments=False,
        include_formatting=True,
        include_links=True,
        include_tables=True,
        favor_precision=True,
        deduplicate=True,
        no_fallback=True,
    )
    if not markdown:
        return None
    normalized = _normalize_markdown(markdown)
    return normalized or None


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


def _normalize_extracted_data(data: Any) -> Optional[Dict[str, Any]]:
    if data is None:
        return None

    candidate: Any = data
    if not isinstance(candidate, dict):
        as_dict = getattr(candidate, "as_dict", None)
        if callable(as_dict):
            candidate = as_dict()
        else:
            candidate = {
                "text": getattr(data, "text", None),
                "title": getattr(data, "title", None),
                "author": getattr(data, "author", None),
                "date": getattr(data, "date", None),
                "language": getattr(data, "language", None),
            }

    if not isinstance(candidate, dict):
        return None

    return {
        "text": candidate.get("text"),
        "title": candidate.get("title"),
        "author": candidate.get("author"),
        "date": candidate.get("date"),
        "language": candidate.get("language"),
        "description": candidate.get("description"),
        "sitename": candidate.get("sitename") or candidate.get("site"),
        "url": candidate.get("url"),
        "hostname": candidate.get("hostname"),
    }


def _normalize_markdown(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _markdown_to_clean_text(markdown: str) -> str:
    text = re.sub(r"```.*?```", lambda match: match.group(0).replace("\n", " "), markdown, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    return _collapse_whitespace(text)


def _extract_links_from_markdown(markdown: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for text, url in MARKDOWN_LINK_RE.findall(markdown):
        item = (_collapse_whitespace(text), _strip_fragment(url))
        if not item[0] or not item[1] or item in seen:
            continue
        seen.add(item)
        links.append({"text": item[0], "url": item[1]})
    return links


def _extract_links_from_html(html: str, base_url: str) -> list[dict[str, str]]:
    parser = HTMLParser(html)
    links: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node in parser.css("a[href]"):
        href = (node.attributes.get("href") or "").strip()
        text = _collapse_whitespace(node.text(separator=" ", strip=True))
        if not href or not text:
            continue
        absolute = _strip_fragment(urljoin(base_url, href))
        try:
            parts = urlsplit(absolute)
        except ValueError:
            continue
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            continue
        item = (text, absolute)
        if item in seen:
            continue
        seen.add(item)
        links.append({"text": text, "url": absolute})
    return links


def _extract_links_from_text(text: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for url in URL_RE.findall(text):
        normalized = _strip_fragment(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        links.append({"text": normalized, "url": normalized})
    return links


def _extract_meta_content(html: str, selectors: Iterable[str]) -> str | None:
    parser = HTMLParser(html)
    for selector in selectors:
        node = parser.css_first(selector)
        if node is None:
            continue
        value = node.attributes.get("content") or node.attributes.get("href")
        normalized = _normalize_optional_string(value)
        if normalized:
            return normalized
    return None


def _extract_title_from_html(html: str) -> str | None:
    parser = HTMLParser(html)
    title_node = parser.css_first("title")
    if title_node is None:
        return None
    return _normalize_optional_string(title_node.text(strip=True))


def _coerce_absolute_url(value: str | None, fallback_url: str) -> str | None:
    if not value:
        return None
    absolute = _strip_fragment(urljoin(fallback_url, value))
    try:
        parts = urlsplit(absolute)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return absolute


def _fallback_metadata(html: str, final_url: str) -> dict[str, str | None]:
    canonical = _coerce_absolute_url(
        _extract_meta_content(
            html,
            [
                'link[rel="canonical"]',
                'meta[property="og:url"]',
            ],
        ),
        final_url,
    )
    description = _extract_meta_content(
        html,
        [
            'meta[name="description"]',
            'meta[property="og:description"]',
            'meta[name="twitter:description"]',
        ],
    )
    site_name = _extract_meta_content(
        html,
        [
            'meta[property="og:site_name"]',
            'meta[name="application-name"]',
        ],
    )
    return {
        "canonical_url": canonical,
        "description": description,
        "site_name": site_name,
        "title": _extract_title_from_html(html),
    }


def _content_stats(markdown: str, links: list[dict[str, str]]) -> dict[str, int]:
    return {
        "chars": len(markdown),
        "words": len(re.findall(r"\S+", markdown)),
        "heading_count": len(re.findall(r"(?m)^#{1,6}\s", markdown)),
        "list_count": len(re.findall(r"(?m)^\s*(?:[-*+]\s|\d+\.\s)", markdown)),
        "code_block_count": markdown.count("```"),
        "link_count": len(links),
    }


def _detect_duplicate_paragraphs(markdown: str) -> bool:
    blocks = [_collapse_whitespace(block) for block in markdown.split("\n\n")]
    blocks = [block for block in blocks if len(block) >= 40]
    return len(blocks) != len(set(blocks))


def _looks_repeated_layout(markdown: str, links: list[dict[str, str]]) -> bool:
    list_count = len(re.findall(r"(?m)^\s*(?:[-*+]\s|\d+\.\s)", markdown))
    repeated_urls = len({link["url"] for link in links}) >= 8 and len(links) >= 10
    return list_count >= 8 or repeated_urls


def _quality_assessment(
    *,
    markdown: str,
    links: list[dict[str, str]],
    canonical_url: str | None,
    site_name: str | None,
    description: str | None,
    extractor_used: str,
) -> tuple[str, list[str]]:
    score = 0
    flags: list[str] = []

    if markdown:
        score += 45
    if len(markdown) >= 400:
        score += 15
    elif len(markdown) >= 150:
        score += 8

    metadata_count = sum(bool(value) for value in (canonical_url, site_name, description))
    score += metadata_count * 8
    if metadata_count < 2:
        flags.append("metadata_sparse")

    if links:
        score += 10
    else:
        flags.append("links_sparse")

    if extractor_used != "trafilatura":
        score -= 10
        flags.append("fallback_used")

    if _detect_duplicate_paragraphs(markdown):
        score -= 12
        flags.append("boilerplate_heavy")

    if _looks_repeated_layout(markdown, links):
        score -= 8
        flags.append("needs_structured_extraction")

    if score >= 65:
        label = "high"
    elif score >= 40:
        label = "medium"
    else:
        label = "low"
    return label, sorted(set(flags))


def _build_markdown_from_readability(html: str, extracted: Dict[str, Any]) -> str | None:
    text = _collapse_whitespace(extracted.get("text") or "")
    if not text:
        return None
    title = _normalize_optional_string(extracted.get("title"))
    if title:
        return _normalize_markdown(f"# {title}\n\n{text}")
    return _normalize_markdown(text)


def _validated_output_mode(output_mode: str) -> str:
    normalized = _collapse_whitespace(output_mode or "text").lower()
    if normalized not in {"text", "evidence"}:
        raise ToolContractError("invalid_url", "output_mode must be 'text' or 'evidence'")
    return normalized


def _read_bounded_bytes(response: Any) -> bytes:
    max_bytes = _fetch_max_bytes()
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                raise ToolContractError("body_too_large", f"content-length exceeds {max_bytes} bytes")
        except ValueError:
            pass

    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise ToolContractError("body_too_large", f"streamed body exceeds {max_bytes} bytes")
    return bytes(body)


def _decode_text(body_bytes: bytes, encoding: str | None) -> str:
    try:
        return body_bytes.decode(encoding or "utf-8", errors="replace")
    except LookupError:
        return body_bytes.decode("utf-8", errors="replace")


def _canonical_redirect_target(current_url: str, location: str | None) -> str:
    if not location or not location.strip():
        raise ToolContractError("redirect_not_allowed", "redirect missing Location header")
    target = urljoin(current_url, location.strip())
    try:
        return _validate_public_target(target, "redirect_not_allowed")
    except ToolContractError as exc:
        if exc.code == "upstream_failure":
            raise ToolContractError("redirect_not_allowed", exc.message) from exc
        raise


def _map_httpx_error(exc: Exception) -> ToolContractError:
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return ToolContractError("timeout", f"{exc.__class__.__name__}: {exc}")
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return ToolContractError("upstream_failure", f"HTTPStatusError status={status}")
    if isinstance(exc, httpx.HTTPError):
        return ToolContractError("upstream_failure", f"{exc.__class__.__name__}: {exc}")
    raise ToolContractError("upstream_failure", f"{exc.__class__.__name__}: {exc}") from exc


def _fetch_url(url: str) -> FetchResult:
    current_url = _validate_public_target(url, "url_not_allowed")
    client = _get_client()
    headers = {"Accept": DEFAULT_ACCEPT}

    for redirect_index in range(_fetch_max_redirects() + 1):
        try:
            with client.stream("GET", current_url, headers=headers) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if redirect_index >= _fetch_max_redirects():
                        raise ToolContractError(
                            "redirect_limit_exceeded",
                            f"exceeded redirect limit {_fetch_max_redirects()}",
                        )
                    current_url = _canonical_redirect_target(current_url, response.headers.get("location"))
                    continue

                response.raise_for_status()

                media_type = _parse_media_type(response.headers.get("content-type"))
                if media_type not in ALLOWED_MEDIA_TYPES:
                    raise ToolContractError("mime_not_allowed", f"media type not allowed: {media_type or 'missing'}")

                body_bytes = _read_bounded_bytes(response)
                return FetchResult(
                    final_url=_strip_fragment(str(response.url)),
                    http_status=response.status_code,
                    content_type=media_type,
                    body_bytes=body_bytes,
                    encoding=response.encoding or "utf-8",
                )
        except ToolContractError:
            raise
        except Exception as exc:
            raise _map_httpx_error(exc) from exc

    raise ToolContractError("redirect_limit_exceeded", f"exceeded redirect limit {_fetch_max_redirects()}")


def _normalize_search_item(item: Any) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    raw_url = _coerce_string(item.get("url") or item.get("link") or item.get("href"))
    if not raw_url:
        return None

    try:
        parts = urlsplit(raw_url)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None

    return {
        "title": _coerce_string(item.get("title") or item.get("name")),
        "url": raw_url,
        "snippet": _coerce_string(item.get("snippet") or item.get("content") or item.get("description")),
        "date": _normalize_optional_string(
            item.get("date") or item.get("published_at") or item.get("published_date") or item.get("published")
        ),
    }


def _normalize_search_payload(payload: Any, max_results: int) -> Dict[str, Any]:
    if isinstance(payload, dict):
        candidates = payload.get("results")
        if not isinstance(candidates, list):
            candidates = payload.get("data")
    elif isinstance(payload, list):
        candidates = payload
    else:
        raise ToolContractError("upstream_failure", "search payload was not a list or object")

    if not isinstance(candidates, list):
        raise ToolContractError("upstream_failure", "search payload did not include a results list")

    results = []
    for item in candidates:
        normalized = _normalize_search_item(item)
        if normalized is None:
            continue
        results.append(normalized)
        if len(results) >= max_results:
            break
    return {"results": results}


def _validated_query(query: str) -> str:
    normalized = _collapse_whitespace(query)
    if not normalized:
        raise ToolContractError("invalid_query", "query must not be blank")
    return normalized


def _validated_max_results(max_results: int) -> int:
    if not isinstance(max_results, int) or max_results < 1 or max_results > 25:
        raise ToolContractError("invalid_query", "max_results must be an integer between 1 and 25")
    return max_results


def _extract_text_payload(fetch_result: FetchResult, include_raw_html: bool) -> Dict[str, Any]:
    body_text = _decode_text(fetch_result.body_bytes, fetch_result.encoding)
    title = None
    byline = None
    published_at = None
    lang = None

    if fetch_result.content_type == "text/plain":
        clean_text = _collapse_whitespace(body_text)
        extractor_used = "plain_text"
    else:
        data = _extract_with_trafilatura(body_text, fetch_result.final_url)
        extractor_used = "trafilatura"
        if data is None:
            data = _extract_with_readability(body_text)
            extractor_used = "readability"
        if data:
            clean_text = _collapse_whitespace(data.get("text") or "")
            title = data.get("title") or None
            byline = data.get("author") or None
            published_at = data.get("date") or None
            lang = data.get("language") or None
        else:
            clean_text = _text_from_html(body_text)
            extractor_used = "plain_text"

    clean_text = _clip_text(clean_text, _fetch_max_clean_text_chars())
    if not clean_text:
        raise ToolContractError("parse_failed", "no readable content after normalization")

    payload: Dict[str, Any] = {
        "final_url": fetch_result.final_url,
        "title": title,
        "byline": byline,
        "published_at": published_at,
        "lang": lang,
        "clean_text": clean_text,
        "extractor_used": extractor_used,
        "content_type": fetch_result.content_type,
        "http_status": fetch_result.http_status,
        "content_sha256": hashlib.sha256(fetch_result.body_bytes).hexdigest(),
    }

    if include_raw_html and fetch_result.content_type in {"text/html", "application/xhtml+xml"}:
        payload["raw_html"] = body_text[: _fetch_max_raw_html_chars()]

    return payload


def _extract_evidence_payload(fetch_result: FetchResult, include_raw_html: bool) -> Dict[str, Any]:
    body_text = _decode_text(fetch_result.body_bytes, fetch_result.encoding)
    body_sha256 = hashlib.sha256(fetch_result.body_bytes).hexdigest()
    title = None
    byline = None
    published_at = None
    lang = None
    canonical_url = None
    site_name = None
    description = None
    links: list[dict[str, str]] = []

    if fetch_result.content_type == "text/plain":
        clean_text = _collapse_whitespace(body_text)
        markdown = clean_text
        extractor_used = "plain_text"
        links = _extract_links_from_text(clean_text)
    else:
        trafilatura_markdown = _extract_markdown_with_trafilatura(body_text, fetch_result.final_url)
        trafilatura_data = _extract_with_trafilatura(body_text, fetch_result.final_url)
        extractor_used = "trafilatura"
        markdown = trafilatura_markdown or ""
        data = trafilatura_data

        if not markdown:
            extractor_used = "readability"
            data = _extract_with_readability(body_text)
            markdown = _build_markdown_from_readability(body_text, data or {}) or ""

        if not markdown:
            extractor_used = "plain_text"
            markdown = _text_from_html(body_text)
            data = None

        metadata = _fallback_metadata(body_text, fetch_result.final_url)
        if data:
            title = _normalize_optional_string(data.get("title"))
            byline = _normalize_optional_string(data.get("author"))
            published_at = _normalize_optional_string(data.get("date"))
            lang = _normalize_optional_string(data.get("language"))
            canonical_url = _coerce_absolute_url(_normalize_optional_string(data.get("url")), fetch_result.final_url)
            site_name = _normalize_optional_string(data.get("sitename") or data.get("hostname"))
            description = _normalize_optional_string(data.get("description"))

        title = title or metadata["title"]
        canonical_url = canonical_url or metadata["canonical_url"] or fetch_result.final_url
        site_name = site_name or metadata["site_name"] or urlsplit(fetch_result.final_url).hostname
        description = description or metadata["description"]
        links = _extract_links_from_markdown(markdown) or _extract_links_from_html(body_text, fetch_result.final_url)

    markdown = _clip_text(_normalize_markdown(markdown), _fetch_max_clean_text_chars())
    clean_text = _clip_text(_markdown_to_clean_text(markdown), _fetch_max_clean_text_chars())
    if not clean_text or not markdown:
        raise ToolContractError("parse_failed", "no readable content after normalization")

    quality_label, quality_flags = _quality_assessment(
        markdown=markdown,
        links=links,
        canonical_url=canonical_url,
        site_name=site_name,
        description=description,
        extractor_used=extractor_used,
    )

    payload: Dict[str, Any] = {
        "final_url": fetch_result.final_url,
        "title": title,
        "byline": byline,
        "published_at": published_at,
        "lang": lang,
        "clean_text": clean_text,
        "extractor_used": extractor_used,
        "content_type": fetch_result.content_type,
        "http_status": fetch_result.http_status,
        "content_sha256": body_sha256,
        "markdown": markdown,
        "canonical_url": canonical_url,
        "site_name": site_name,
        "description": description,
        "links": links,
        "quality_label": quality_label,
        "quality_flags": quality_flags,
        "content_stats": _content_stats(markdown, links),
    }

    if include_raw_html and fetch_result.content_type in {"text/html", "application/xhtml+xml"}:
        payload["raw_html"] = body_text[: _fetch_max_raw_html_chars()]

    return payload


@mcp.tool(name="search.web")
def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web via LiteLLM's /v1/search proxy."""

    validated_query = _validated_query(query)
    validated_max_results = _validated_max_results(max_results)
    api_base = os.getenv("LITELLM_SEARCH_API_BASE", DEFAULT_SEARCH_API_BASE)
    api_key = os.getenv("LITELLM_SEARCH_API_KEY", "dummy")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = _get_client().post(
            api_base,
            json={"query": validated_query, "max_results": validated_max_results},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
    except ToolContractError:
        raise
    except Exception as exc:
        raise _map_httpx_error(exc) from exc

    return _normalize_search_payload(payload, validated_max_results)


@mcp.tool(name="web.fetch")
def web_fetch(url: str, include_raw_html: bool = False, output_mode: str = "text") -> Dict[str, Any]:
    """Fetch a public URL and return bounded cleaned text and metadata."""

    try:
        normalized_url = _split_url(url.strip(), "invalid_url")
    except ToolContractError:
        raise
    validated_output_mode = _validated_output_mode(output_mode)
    validated_url = urlunsplit((normalized_url.scheme, normalized_url.netloc, normalized_url.path, normalized_url.query, ""))
    fetch_result = _fetch_url(validated_url)
    if validated_output_mode == "evidence":
        return _extract_evidence_payload(fetch_result, include_raw_html)
    return _extract_text_payload(fetch_result, include_raw_html)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
