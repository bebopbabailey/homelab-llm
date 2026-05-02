#!/usr/bin/env python3
"""Localhost-only MCP backend for media and web retrieval tools."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlsplit, urlunsplit

import httpx
import trafilatura
from mcp.server.fastmcp import FastMCP
from readability import Document
from selectolax.parser import HTMLParser
from youtube_transcript_api import YouTubeTranscriptApi

MCP_SERVER_NAME = "media-fetch"
DEFAULT_USER_AGENT = "homelab-llm-media-fetch/1.0"
DEFAULT_ACCEPT = "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1"
DEFAULT_SEARXNG_API_BASE = "http://127.0.0.1:8888/search"
DEFAULT_VECTOR_DB_API_BASE = "http://192.168.1.72:55440"
ALLOWED_MEDIA_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
YOUTUBE_SOURCE_TYPE = "youtube"
WEB_SOURCE_TYPE = "web_research"
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_NOISE_RE = re.compile(r"^[\s\-–—.,:;!?()\[\]\"']*$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
URL_RE = re.compile(r"https?://[^\s)>\"]+")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")

mcp = FastMCP(MCP_SERVER_NAME)

_HTTP_CLIENT: httpx.Client | None = None


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
    return _env_int("MEDIA_FETCH_MAX_BYTES", 2_097_152)


def _fetch_max_clean_text_chars() -> int:
    return _env_int("MEDIA_FETCH_MAX_CLEAN_TEXT_CHARS", 50_000)


def _fetch_max_raw_html_chars() -> int:
    return _env_int("MEDIA_FETCH_MAX_RAW_HTML_CHARS", 200_000)


def _fetch_max_redirects() -> int:
    return _env_int("MEDIA_FETCH_MAX_REDIRECTS", 5)


def _fetch_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=float(_env_int("MEDIA_FETCH_CONNECT_TIMEOUT", 5)),
        read=float(_env_int("MEDIA_FETCH_READ_TIMEOUT", 20)),
        write=float(_env_int("MEDIA_FETCH_WRITE_TIMEOUT", 5)),
        pool=float(_env_int("MEDIA_FETCH_POOL_TIMEOUT", 5)),
    )


def _fetch_limits() -> httpx.Limits:
    return httpx.Limits(
        max_connections=_env_int("MEDIA_FETCH_MAX_CONNECTIONS", 10),
        max_keepalive_connections=_env_int("MEDIA_FETCH_MAX_KEEPALIVE_CONNECTIONS", 5),
        keepalive_expiry=float(_env_int("MEDIA_FETCH_KEEPALIVE_EXPIRY", 15)),
    )


def _search_api_base() -> str:
    return os.getenv("MEDIA_FETCH_SEARXNG_API_BASE", DEFAULT_SEARXNG_API_BASE).rstrip("/")


def _search_categories() -> str:
    return os.getenv("MEDIA_FETCH_SEARXNG_CATEGORIES", "general").strip() or "general"


def _search_language() -> str | None:
    value = os.getenv("MEDIA_FETCH_SEARXNG_LANGUAGE", "").strip()
    return value or None


def _vector_db_api_base() -> str:
    return os.getenv("MEDIA_FETCH_VECTOR_DB_API_BASE", DEFAULT_VECTOR_DB_API_BASE).rstrip("/")


def _vector_db_write_bearer_token() -> str:
    return os.getenv("MEDIA_FETCH_VECTOR_DB_WRITE_BEARER_TOKEN", "").strip()


def _session_ttl_seconds() -> int:
    return _env_int("MEDIA_FETCH_SESSION_TTL_SECONDS", 86_400)


def _chunk_target_chars() -> int:
    return _env_int("MEDIA_FETCH_CHUNK_TARGET_CHARS", 1_800)


def _chunk_overlap_chars() -> int:
    return _env_int("MEDIA_FETCH_CHUNK_OVERLAP_CHARS", 200)


def _build_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": os.getenv("MEDIA_FETCH_USER_AGENT", DEFAULT_USER_AGENT)},
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
    return re.sub(r"\s+", " ", text or "").strip()


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


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _hash_token(*parts: str) -> str:
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _split_url(url: str, error_code: str) -> Any:
    candidate = _strip_fragment((url or "").strip())
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
    return _collapse_whitespace(parser.text(separator=" ", strip=True))


def _normalize_extracted_data(data: Any) -> dict[str, Any] | None:
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


def _extract_with_trafilatura(html: str, url: str) -> dict[str, Any] | None:
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


def _normalize_markdown(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def _extract_with_readability(html: str) -> dict[str, Any] | None:
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
        _extract_meta_content(html, ['link[rel="canonical"]', 'meta[property="og:url"]']),
        final_url,
    )
    description = _extract_meta_content(
        html,
        ['meta[name="description"]', 'meta[property="og:description"]', 'meta[name="twitter:description"]'],
    )
    site_name = _extract_meta_content(html, ['meta[property="og:site_name"]', 'meta[name="application-name"]'])
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


def _build_markdown_from_readability(extracted: dict[str, Any]) -> str | None:
    text = _collapse_whitespace(str(extracted.get("text") or ""))
    if not text:
        return None
    title = _normalize_optional_string(extracted.get("title"))
    if title:
        return _normalize_markdown(f"# {title}\n\n{text}")
    return _normalize_markdown(text)


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


def _normalize_search_item(item: Any) -> dict[str, Any] | None:
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
        "engine": _normalize_optional_string(item.get("engine")),
    }


def _normalize_search_payload(payload: Any, max_results: int) -> dict[str, Any]:
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


def _validated_max_results(max_results: int, *, upper_bound: int = 25) -> int:
    if not isinstance(max_results, int) or max_results < 1 or max_results > upper_bound:
        raise ToolContractError("invalid_query", f"max_results must be an integer between 1 and {upper_bound}")
    return max_results


def _validated_conversation_id(conversation_id: str) -> str:
    normalized = _collapse_whitespace(conversation_id)
    if not normalized:
        raise ToolContractError("invalid_conversation", "conversation_id is required")
    if len(normalized) > 200:
        raise ToolContractError("invalid_conversation", "conversation_id exceeds 200 characters")
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", normalized):
        raise ToolContractError(
            "invalid_conversation",
            "conversation_id may contain only letters, numbers, dot, underscore, colon, and hyphen",
        )
    return normalized


def _research_document_id(conversation_id: str) -> str:
    return f"research:{_validated_conversation_id(conversation_id)}"


def _timestamp_now() -> str:
    return datetime.now(UTC).isoformat()


def _expires_at(ttl_seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat()


def _extract_video_id(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise ToolContractError("invalid_url", "url is required")
    try:
        parsed = urlparse(candidate)
    except ValueError as exc:
        raise ToolContractError("invalid_url", f"invalid URL parse: {exc.__class__.__name__}") from exc
    host = parsed.netloc.lower()
    if not host or parsed.scheme not in {"http", "https"}:
        raise ToolContractError("invalid_url", "only absolute http(s) YouTube URLs are allowed")
    path_parts = [part for part in parsed.path.split("/") if part]
    video_id: str | None = None
    if host.endswith("youtu.be"):
        if path_parts:
            video_id = path_parts[0]
    elif host.endswith("youtube.com"):
        if path_parts[:1] == ["watch"]:
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif path_parts[:1] in (["shorts"], ["live"], ["embed"]):
            video_id = path_parts[1] if len(path_parts) > 1 else None
        elif "v" in parse_qs(parsed.query):
            video_id = parse_qs(parsed.query).get("v", [None])[0]
    if not isinstance(video_id, str):
        raise ToolContractError("unsupported_url", "expected a supported single-video YouTube URL")
    video_id = video_id.strip()
    if not _YOUTUBE_ID_RE.fullmatch(video_id):
        raise ToolContractError("unsupported_url", "expected a supported single-video YouTube URL")
    return video_id


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _normalize_segment_payload(item: dict[str, Any]) -> dict[str, Any] | None:
    text = _collapse_whitespace(str(item.get("text") or ""))
    if not text or _NOISE_RE.fullmatch(text):
        return None
    start = float(item.get("start") or 0.0)
    duration = float(item.get("duration") or 0.0)
    return {
        "text": text,
        "start": start,
        "duration": duration,
        "timestamp_label": _format_timestamp(start),
    }


def _fetch_transcript_payload(url: str) -> dict[str, Any]:
    video_id = _extract_video_id(url)
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
    except Exception as exc:
        message = str(exc)
        if "No transcripts" in message or "Subtitles are disabled" in message:
            raise ToolContractError("no_transcript", f"no usable transcript for video {video_id}") from exc
        raise ToolContractError("upstream_failure", f"{exc.__class__.__name__}: {message}") from exc
    transcript = None
    caption_type = None
    for candidate in transcript_list:
        if not getattr(candidate, "is_generated", False):
            transcript = candidate
            caption_type = "manual"
            break
    if transcript is None:
        for candidate in transcript_list:
            transcript = candidate
            caption_type = "generated" if getattr(candidate, "is_generated", False) else "manual"
            break
    if transcript is None:
        raise ToolContractError("no_transcript", f"no usable transcript for video {video_id}")
    try:
        fetched = transcript.fetch()
    except Exception as exc:
        raise ToolContractError("upstream_failure", f"{exc.__class__.__name__}: {exc}") from exc
    raw_segments = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
    segments = []
    lines = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_segment_payload(item)
        if not normalized:
            continue
        segments.append(normalized)
        lines.append(f"[{normalized['timestamp_label']}] {normalized['text']}")
    if not segments:
        raise ToolContractError("no_transcript", f"no non-empty transcript lines for video {video_id}")
    return {
        "video_id": video_id,
        "source_url": f"https://youtu.be/{video_id}",
        "transcript_text": "\n".join(lines),
        "language": getattr(transcript, "language", "") or "Unknown",
        "language_code": getattr(transcript, "language_code", "") or "",
        "caption_type": caption_type or "unknown",
        "segments": segments,
    }


def _extract_evidence_payload(fetch_result: FetchResult, include_raw_html: bool) -> dict[str, Any]:
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
            markdown = _build_markdown_from_readability(data or {}) or ""
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
    payload: dict[str, Any] = {
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
        "canonical_url": canonical_url or fetch_result.final_url,
        "site_name": site_name,
        "description": description,
        "links": links,
        "quality_label": quality_label,
        "quality_flags": quality_flags,
        "content_stats": _content_stats(markdown, links),
        "fetched_at_utc": _timestamp_now(),
    }
    if include_raw_html and fetch_result.content_type in {"text/html", "application/xhtml+xml"}:
        payload["raw_html"] = body_text[: _fetch_max_raw_html_chars()]
    return payload


def _http_json(
    method: str,
    url: str,
    *,
    json_payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    client = _get_client()
    try:
        response = client.request(method, url, json=json_payload, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
    except ToolContractError:
        raise
    except Exception as exc:
        raise _map_httpx_error(exc) from exc
    if not isinstance(payload, dict):
        raise ToolContractError("upstream_failure", "expected JSON object response")
    return payload


def _vector_db_headers(*, write: bool) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if write:
        token = _vector_db_write_bearer_token()
        if not token:
            raise ToolContractError("config_error", "MEDIA_FETCH_VECTOR_DB_WRITE_BEARER_TOKEN is required for writes")
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _search_web_raw(query: str, max_results: int) -> dict[str, Any]:
    validated_query = _validated_query(query)
    validated_max_results = _validated_max_results(max_results)
    params: dict[str, Any] = {
        "q": validated_query,
        "format": "json",
        "categories": _search_categories(),
    }
    language = _search_language()
    if language:
        params["language"] = language
    payload = _http_json("GET", _search_api_base(), params=params)
    normalized = _normalize_search_payload(payload, validated_max_results)
    normalized["query"] = validated_query
    normalized["provider"] = "searxng"
    normalized["categories"] = _search_categories()
    return normalized


def _web_fetch_raw(url: str, include_raw_html: bool) -> dict[str, Any]:
    normalized_url = _split_url(url.strip(), "invalid_url")
    validated_url = urlunsplit((normalized_url.scheme, normalized_url.netloc, normalized_url.path, normalized_url.query, ""))
    fetch_result = _fetch_url(validated_url)
    payload = _extract_evidence_payload(fetch_result, include_raw_html)
    payload["requested_url"] = validated_url
    return payload


def _heading_from_block(block: str, current_heading: str) -> str:
    for line in block.splitlines():
        match = HEADING_RE.match(line.strip())
        if match:
            return _collapse_whitespace(match.group(1))
    return current_heading


def _chunk_markdown(markdown: str, *, document_id: str, page_key: str, base_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = _normalize_markdown(markdown)
    if not normalized:
        return []
    blocks = [block.strip() for block in normalized.split("\n\n") if block.strip()]
    if not blocks:
        blocks = [normalized]
    target = max(600, _chunk_target_chars())
    overlap = max(0, min(_chunk_overlap_chars(), target // 2))
    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    current_len = 0
    current_heading = ""
    cursor = 0

    def flush() -> None:
        nonlocal current, current_len, cursor
        if not current:
            return
        text = _normalize_markdown("\n\n".join(current))
        if not text:
            current = []
            current_len = 0
            return
        start = normalized.find(text, cursor)
        if start < 0:
            start = cursor
        end = min(len(normalized), start + len(text))
        chunk_index = len(chunks)
        chunk_id = _hash_token(document_id, page_key, str(chunk_index), text[:120])
        chunks.append(
            {
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "text": text,
                "section_title": current_heading,
                "char_start": start,
                "char_end": end,
                "metadata": dict(base_metadata),
            }
        )
        cursor = end
        if overlap and len(text) > overlap:
            tail = text[-overlap:].strip()
            current = [tail] if tail else []
            current_len = len(tail)
        else:
            current = []
            current_len = 0

    for block in blocks:
        current_heading = _heading_from_block(block, current_heading)
        addition = len(block) + (2 if current else 0)
        if current and current_len + addition > target:
            flush()
        current.append(block)
        current_len += addition
    flush()
    return chunks


def _normalize_session_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(documents, list) or not documents:
        raise ToolContractError("invalid_documents", "documents must be a non-empty list of cleaned fetch payloads")
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in documents:
        if not isinstance(raw, dict):
            raise ToolContractError("invalid_documents", "documents entries must be objects")
        canonical_url = _normalize_optional_string(raw.get("canonical_url") or raw.get("final_url") or raw.get("requested_url"))
        if not canonical_url:
            raise ToolContractError("invalid_documents", "each document requires canonical_url, final_url, or requested_url")
        content_sha256 = _normalize_optional_string(raw.get("content_sha256")) or _hash_token(
            canonical_url,
            _coerce_string(raw.get("markdown") or raw.get("clean_text")),
        )
        dedupe_key = (canonical_url, content_sha256)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(
            {
                "canonical_url": canonical_url,
                "final_url": _normalize_optional_string(raw.get("final_url")) or canonical_url,
                "requested_url": _normalize_optional_string(raw.get("requested_url")) or canonical_url,
                "title": _normalize_optional_string(raw.get("title")) or "",
                "site_name": _normalize_optional_string(raw.get("site_name")) or "",
                "description": _normalize_optional_string(raw.get("description")) or "",
                "markdown": _normalize_optional_string(raw.get("markdown")) or "",
                "clean_text": _normalize_optional_string(raw.get("clean_text")) or "",
                "quality_label": _normalize_optional_string(raw.get("quality_label")) or "unknown",
                "quality_flags": list(raw.get("quality_flags") or []),
                "content_stats": dict(raw.get("content_stats") or {}),
                "extractor_used": _normalize_optional_string(raw.get("extractor_used")) or "unknown",
                "content_sha256": content_sha256,
                "content_type": _normalize_optional_string(raw.get("content_type")) or "",
                "http_status": _safe_int(raw.get("http_status")) or 200,
                "fetched_at_utc": _normalize_optional_string(raw.get("fetched_at_utc")) or _timestamp_now(),
                "lang": _normalize_optional_string(raw.get("lang")) or "",
                "byline": _normalize_optional_string(raw.get("byline")) or "",
                "published_at": _normalize_optional_string(raw.get("published_at")) or "",
                "links": list(raw.get("links") or []),
            }
        )
    if not normalized:
        raise ToolContractError("invalid_documents", "no unique cleaned documents survived normalization")
    return normalized


def _build_upsert_documents(conversation_id: str, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    session_id = _validated_conversation_id(conversation_id)
    document_id = _research_document_id(session_id)
    ttl_seconds = _session_ttl_seconds()
    expires_at_utc = _expires_at(ttl_seconds)
    upserts: list[dict[str, Any]] = []
    for raw in _normalize_session_documents(documents):
        markdown = raw["markdown"] or raw["clean_text"]
        page_key = _hash_token(raw["canonical_url"], raw["content_sha256"])
        base_metadata = {
            "conversation_id": session_id,
            "canonical_url": raw["canonical_url"],
            "final_url": raw["final_url"],
            "requested_url": raw["requested_url"],
            "site_name": raw["site_name"],
            "description": raw["description"],
            "quality_label": raw["quality_label"],
            "quality_flags": raw["quality_flags"],
            "extractor_used": raw["extractor_used"],
            "content_sha256": raw["content_sha256"],
            "content_type": raw["content_type"],
            "fetched_at_utc": raw["fetched_at_utc"],
            "published_at": raw["published_at"],
            "lang": raw["lang"],
            "page_key": page_key,
            "expires_at_utc": expires_at_utc,
            "session_ttl_seconds": ttl_seconds,
        }
        chunks = _chunk_markdown(markdown, document_id=document_id, page_key=page_key, base_metadata=base_metadata)
        if not chunks:
            raise ToolContractError("invalid_documents", f"document {raw['canonical_url']} did not produce any chunks")
        upserts.append(
            {
                "document_id": document_id,
                "source_type": WEB_SOURCE_TYPE,
                "source": "media-fetch-mcp",
                "source_thread_id": session_id,
                "timestamp_utc": _timestamp_now(),
                "title": raw["title"],
                "uri": raw["canonical_url"],
                "metadata": {
                    "conversation_id": session_id,
                    "expires_at_utc": expires_at_utc,
                    "session_ttl_seconds": ttl_seconds,
                    "last_upsert_source_url": raw["canonical_url"],
                    "last_upsert_site_name": raw["site_name"],
                },
                "chunks": chunks,
            }
        )
    return upserts


def _normalize_search_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_hits = payload.get("hits")
    if not isinstance(raw_hits, list):
        raise ToolContractError("upstream_failure", "vector-db search response did not include hits")
    normalized: list[dict[str, Any]] = []
    for index, hit in enumerate(raw_hits, start=1):
        if not isinstance(hit, dict):
            continue
        metadata = dict(hit.get("metadata") or {})
        spans = dict(hit.get("spans") or {})
        source_url = (
            metadata.get("canonical_url")
            or metadata.get("final_url")
            or hit.get("source_uri")
            or hit.get("uri")
            or ""
        )
        normalized.append(
            {
                "rank": index,
                "score": hit.get("score", hit.get("rrf_score")),
                "document_id": _coerce_string(hit.get("document_id") or hit.get("doc_id")),
                "chunk_id": _coerce_string(hit.get("chunk_id")),
                "title": _coerce_string(hit.get("title")),
                "source_url": _coerce_string(source_url),
                "site_name": _coerce_string(metadata.get("site_name")),
                "section_title": _coerce_string(hit.get("section_title")),
                "timestamp_label": _coerce_string(hit.get("timestamp_label") or spans.get("timestamp_label")),
                "text": _coerce_string(hit.get("text")),
                "metadata": metadata,
                "spans": spans,
            }
        )
    return normalized


def _vector_db_upsert(conversation_id: str, documents: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {"documents": _build_upsert_documents(conversation_id, documents)}
    response = _http_json(
        "POST",
        f"{_vector_db_api_base()}/v1/memory/upsert",
        json_payload=payload,
        headers=_vector_db_headers(write=True),
    )
    response["conversation_id"] = _validated_conversation_id(conversation_id)
    response["document_id"] = _research_document_id(conversation_id)
    return response


def _vector_db_search(
    conversation_id: str,
    query: str,
    *,
    profile: str = "balanced",
    top_k: int = 6,
    vector_search_mode: str = "auto",
) -> dict[str, Any]:
    validated_profile = profile if profile in {"precise", "balanced", "broad"} else "balanced"
    validated_top_k = _validated_max_results(top_k, upper_bound=20)
    payload = _http_json(
        "POST",
        f"{_vector_db_api_base()}/v1/memory/search",
        json_payload={
            "query": _validated_query(query),
            "profile": validated_profile,
            "top_k": validated_top_k,
            "document_id": _research_document_id(conversation_id),
            "source_type": WEB_SOURCE_TYPE,
            "render_citations": False,
            "vector_search_mode": vector_search_mode,
        },
        headers=_vector_db_headers(write=False),
    )
    return {
        "conversation_id": _validated_conversation_id(conversation_id),
        "document_id": _research_document_id(conversation_id),
        "query": payload.get("query") or query,
        "profile": payload.get("profile") or validated_profile,
        "hits": _normalize_search_hits(payload),
    }


def _vector_db_delete(conversation_id: str) -> dict[str, Any]:
    response = _http_json(
        "POST",
        f"{_vector_db_api_base()}/v1/memory/delete",
        json_payload={"document_id": _research_document_id(conversation_id)},
        headers=_vector_db_headers(write=True),
    )
    response["conversation_id"] = _validated_conversation_id(conversation_id)
    response["document_id"] = _research_document_id(conversation_id)
    return response


def _summarize_fetched_sources(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for item in documents:
        summaries.append(
            {
                "title": item.get("title"),
                "source_url": item.get("canonical_url") or item.get("final_url"),
                "site_name": item.get("site_name"),
                "quality_label": item.get("quality_label"),
                "extractor_used": item.get("extractor_used"),
            }
        )
    return summaries


@mcp.tool(name="youtube.transcript")
def youtube_transcript(url: str) -> dict[str, Any]:
    """Fetch the full transcript for a supported YouTube video URL."""

    return _fetch_transcript_payload(url)


@mcp.tool(name="media-fetch.web.search")
def media_fetch_web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the live web via direct SearXNG JSON results."""

    return _search_web_raw(query, max_results)


@mcp.tool(name="media-fetch.web.fetch")
def media_fetch_web_fetch(url: str, include_raw_html: bool = False) -> dict[str, Any]:
    """Fetch a public URL and return cleaned evidence payloads."""

    return _web_fetch_raw(url, include_raw_html)


@mcp.tool(name="media-fetch.web.session.upsert")
def media_fetch_web_session_upsert(conversation_id: str, documents: list[dict[str, Any]]) -> dict[str, Any]:
    """Store cleaned fetch payloads in the per-conversation research session."""

    return _vector_db_upsert(conversation_id, documents)


@mcp.tool(name="media-fetch.web.session.search")
def media_fetch_web_session_search(
    conversation_id: str,
    query: str,
    profile: str = "balanced",
    top_k: int = 6,
    vector_search_mode: str = "auto",
) -> dict[str, Any]:
    """Retrieve chunk-level evidence from the per-conversation research session."""

    return _vector_db_search(
        conversation_id,
        query,
        profile=profile,
        top_k=top_k,
        vector_search_mode=vector_search_mode,
    )


@mcp.tool(name="media-fetch.web.session.delete")
def media_fetch_web_session_delete(conversation_id: str) -> dict[str, Any]:
    """Delete the per-conversation research session from vector-db."""

    return _vector_db_delete(conversation_id)


@mcp.tool(name="media-fetch.web.quick")
def media_fetch_web_quick(
    conversation_id: str,
    query: str,
    search_max_results: int = 5,
    fetch_max_results: int = 3,
    profile: str = "balanced",
    top_k: int = 6,
) -> dict[str, Any]:
    """Search, fetch, persist, and return top chunk evidence for one query."""

    search_payload = _search_web_raw(query, search_max_results)
    selected = search_payload["results"][: _validated_max_results(fetch_max_results, upper_bound=10)]
    documents = [_web_fetch_raw(item["url"], include_raw_html=False) for item in selected]
    upsert_payload = _vector_db_upsert(conversation_id, documents)
    evidence_payload = _vector_db_search(conversation_id, query, profile=profile, top_k=top_k)
    return {
        "conversation_id": _validated_conversation_id(conversation_id),
        "document_id": _research_document_id(conversation_id),
        "query": _validated_query(query),
        "search_result_count": len(search_payload["results"]),
        "fetched_count": len(documents),
        "stored": {
            "documents": upsert_payload.get("documents"),
            "chunks": upsert_payload.get("chunks"),
        },
        "sources": _summarize_fetched_sources(documents),
        "evidence": evidence_payload["hits"],
    }


@mcp.tool(name="media-fetch.web.research")
def media_fetch_web_research(
    conversation_id: str,
    query: str,
    search_max_results: int = 8,
    fetch_max_results: int = 5,
    profile: str = "broad",
    top_k: int = 8,
) -> dict[str, Any]:
    """Build a broader research session and return corpus metadata plus evidence."""

    search_payload = _search_web_raw(query, search_max_results)
    selected = search_payload["results"][: _validated_max_results(fetch_max_results, upper_bound=12)]
    documents = [_web_fetch_raw(item["url"], include_raw_html=False) for item in selected]
    upsert_payload = _vector_db_upsert(conversation_id, documents)
    evidence_payload = _vector_db_search(conversation_id, query, profile=profile, top_k=top_k)
    return {
        "conversation_id": _validated_conversation_id(conversation_id),
        "document_id": _research_document_id(conversation_id),
        "query": _validated_query(query),
        "search": search_payload,
        "fetched_documents": _summarize_fetched_sources(documents),
        "stored": {
            "documents": upsert_payload.get("documents"),
            "chunks": upsert_payload.get("chunks"),
        },
        "retrieval": evidence_payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the media-fetch MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport to run",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()
    if args.transport == "streamable-http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(args.transport)


if __name__ == "__main__":
    main()
