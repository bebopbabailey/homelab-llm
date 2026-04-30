#!/usr/bin/env python3
"""Localhost-only MCP backend for media retrieval tools."""

from __future__ import annotations

import argparse
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi

MCP_SERVER_NAME = "media-fetch"
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_NOISE_RE = re.compile(r"^[\s\-–—.,:;!?()\[\]\"']*$")

mcp = FastMCP(MCP_SERVER_NAME)


class ToolContractError(RuntimeError):
    """Stable tool error with a machine-parseable code prefix."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


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


def _normalize_segment(item: dict[str, Any]) -> str | None:
    text = _collapse_whitespace(str(item.get("text") or ""))
    if not text or _NOISE_RE.fullmatch(text):
        return None
    start = float(item.get("start") or 0.0)
    return f"[{_format_timestamp(start)}] {text}"


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


@mcp.tool(name="youtube.transcript")
def youtube_transcript(url: str) -> dict[str, Any]:
    return _fetch_transcript_payload(url)


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
