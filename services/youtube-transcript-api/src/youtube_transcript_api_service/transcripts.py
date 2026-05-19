from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_NOISE_RE = re.compile(r"^[\s\-.,:;!?()\[\]\"']*$")


class TranscriptError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class TranscriptDocument:
    source_type: str
    source_id: str
    canonical_url: str
    language: str
    language_code: str
    caption_type: str
    transcript_text: str
    content_hash: str
    segments: list[dict[str, Any]]

    def model_payload(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "canonical_url": self.canonical_url,
            "language": self.language,
            "language_code": self.language_code,
            "caption_type": self.caption_type,
            "transcript_text": self.transcript_text,
            "content_hash": self.content_hash,
            "segments": self.segments,
        }


def extract_video_id(url: str) -> str:
    candidate = (url or "").strip()
    try:
        parsed = urlparse(candidate)
    except ValueError as exc:
        raise TranscriptError("invalid_url", f"invalid URL parse: {exc.__class__.__name__}", 400) from exc
    host = parsed.netloc.lower()
    if parsed.scheme not in {"http", "https"} or not host:
        raise TranscriptError("invalid_url", "only absolute http(s) YouTube URLs are supported", 400)
    path_parts = [part for part in parsed.path.split("/") if part]
    query = parse_qs(parsed.query)
    video_id: str | None = None
    if host.endswith("youtu.be"):
        video_id = path_parts[0] if path_parts else None
    elif host.endswith("youtube.com"):
        if path_parts[:1] == ["watch"]:
            video_id = query.get("v", [None])[0]
        elif path_parts[:1] in (["shorts"], ["live"], ["embed"]):
            video_id = path_parts[1] if len(path_parts) > 1 else None
        elif "v" in query:
            video_id = query.get("v", [None])[0]
    if not isinstance(video_id, str) or not _YOUTUBE_ID_RE.fullmatch(video_id.strip()):
        raise TranscriptError("unsupported_url", "expected one supported single-video YouTube URL", 400)
    return video_id.strip()


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_segment(item: dict[str, Any]) -> dict[str, Any] | None:
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


def fetch_transcript(url: str) -> TranscriptDocument:
    video_id = extract_video_id(url)
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
    except Exception as exc:
        message = str(exc)
        if "No transcripts" in message or "Subtitles are disabled" in message:
            raise TranscriptError("no_transcript", f"no usable transcript for video {video_id}", 404) from exc
        raise TranscriptError("upstream_failure", f"{exc.__class__.__name__}: {message}", 502) from exc

    transcript = None
    caption_type = "unknown"
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
        raise TranscriptError("no_transcript", f"no usable transcript for video {video_id}", 404)

    try:
        fetched = transcript.fetch()
    except Exception as exc:
        raise TranscriptError("upstream_failure", f"{exc.__class__.__name__}: {exc}", 502) from exc

    raw_segments = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
    segments: list[dict[str, Any]] = []
    lines: list[str] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        segment = _normalize_segment(item)
        if segment is None:
            continue
        segments.append(segment)
        lines.append(f"[{segment['timestamp_label']}] {segment['text']}")
    if not segments:
        raise TranscriptError("no_transcript", f"no non-empty transcript lines for video {video_id}", 404)

    transcript_text = "\n".join(lines)
    return TranscriptDocument(
        source_type="youtube",
        source_id=video_id,
        canonical_url=f"https://youtu.be/{video_id}",
        language=getattr(transcript, "language", "") or "Unknown",
        language_code=getattr(transcript, "language_code", "") or "",
        caption_type=caption_type,
        transcript_text=transcript_text,
        content_hash=hashlib.sha256(transcript_text.encode("utf-8")).hexdigest(),
        segments=segments,
    )
