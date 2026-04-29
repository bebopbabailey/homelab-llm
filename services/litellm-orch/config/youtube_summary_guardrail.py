from __future__ import annotations

import importlib.util
import json
import logging
import math
import os
import re
import sys
import types
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks
from youtube_transcript_api import YouTubeTranscriptApi

try:
    from config.prompt_guardrail import _render_prompt_messages
except ModuleNotFoundError:
    _PROMPT_PATH = Path(__file__).with_name("prompt_guardrail.py")
    _PROMPT_SPEC = importlib.util.spec_from_file_location("prompt_guardrail", _PROMPT_PATH)
    if _PROMPT_SPEC is None or _PROMPT_SPEC.loader is None:
        raise ImportError(f"Unable to load prompt_guardrail from {_PROMPT_PATH}")
    _PROMPT_MODULE = importlib.util.module_from_spec(_PROMPT_SPEC)
    _PROMPT_SPEC.loader.exec_module(_PROMPT_MODULE)
    _render_prompt_messages = _PROMPT_MODULE._render_prompt_messages


TASK_YOUTUBE_SUMMARY_ALIAS = "task-youtube-summary"
PROMPT_ID = "task-youtube-summary"
MIN_RESPONSE_OUTPUT_TOKENS = 2048
MIN_CHAT_OUTPUT_TOKENS = 2048
SINGLE_PASS_TRANSCRIPT_TOKENS = 18000
CHUNK_TARGET_TOKENS = 8000
CHUNK_SUMMARY_MAX_OUTPUT_TOKENS = 900
FINAL_SUMMARY_MAX_OUTPUT_TOKENS = 2400
_YOUTUBE_URL_RE = re.compile(r"https?://[^\s<>()\[\]{}]+", re.IGNORECASE)
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
logger = logging.getLogger("youtube_summary_guardrail")
_STATE_MODULE_NAME = "_youtube_summary_guardrail_state"
_STATE = sys.modules.get(_STATE_MODULE_NAME)
if _STATE is None:
    _STATE = types.SimpleNamespace(request_contexts={}, lock=Lock())
    sys.modules[_STATE_MODULE_NAME] = _STATE
_REQUEST_CONTEXTS: dict[int, dict[str, Any]] = _STATE.request_contexts
_LOCK: Lock = _STATE.lock


class TranscriptFetchResult:
    def __init__(
        self,
        *,
        video_id: str,
        transcript_text: str,
        transcript_language: str,
        transcript_language_code: str,
        caption_type: str,
        was_translated: bool,
        token_estimate: int,
        segments: list[dict[str, Any]],
    ) -> None:
        self.video_id = video_id
        self.transcript_text = transcript_text
        self.transcript_language = transcript_language
        self.transcript_language_code = transcript_language_code
        self.caption_type = caption_type
        self.was_translated = was_translated
        self.token_estimate = token_estimate
        self.segments = segments


def _normalize_model_name(model: Any) -> str:
    if not isinstance(model, str):
        return ""
    normalized = model.strip().lower()
    if "/" in normalized:
        normalized = normalized.rsplit("/", 1)[-1]
    return normalized


def _strip_provider_prefix(model: str) -> str:
    return model.rsplit("/", 1)[-1] if "/" in model else model


def _is_target_model(model: Any) -> bool:
    return _normalize_model_name(model) == TASK_YOUTUBE_SUMMARY_ALIAS


def _coerce_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("value")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if isinstance(content, dict):
        text = content.get("text") or content.get("value")
        if isinstance(text, str):
            return text
        return _coerce_text(content.get("content"))
    return str(content)


def _extract_latest_user_text_from_messages(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        text = _coerce_text(message.get("content")).strip()
        if text:
            return text
    return ""


def _extract_latest_user_text_from_input(input_value: Any) -> str:
    if isinstance(input_value, str):
        return input_value.strip()
    if not isinstance(input_value, list):
        return ""
    for item in reversed(input_value):
        if not isinstance(item, dict) or item.get("role") != "user":
            continue
        text = _coerce_text(item.get("content")).strip()
        if text:
            return text
    return ""


def _clean_extracted_url(url: str) -> str:
    return url.rstrip("),.;!?:]}")


def _extract_urls(text: str) -> list[str]:
    return [_clean_extracted_url(match.group(0)) for match in _YOUTUBE_URL_RE.finditer(text or "")]


def _extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    if host.endswith("youtu.be"):
        if path_parts:
            candidate = path_parts[0]
        else:
            return None
    elif host.endswith("youtube.com"):
        if path_parts[:1] == ["watch"]:
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif path_parts[:1] in (["shorts"], ["live"], ["embed"]):
            candidate = path_parts[1] if len(path_parts) > 1 else None
        else:
            candidate = parse_qs(parsed.query).get("v", [None])[0]
    else:
        return None
    if not isinstance(candidate, str):
        return None
    candidate = candidate.strip()
    if not _YOUTUBE_ID_RE.fullmatch(candidate):
        return None
    return candidate


def _remove_urls(text: str) -> str:
    return _YOUTUBE_URL_RE.sub(" ", text or "")


def _extract_url_and_focus_request(text: str) -> tuple[str, str, str]:
    urls = _extract_urls(text)
    if not urls:
        raise HTTPException(status_code=400, detail=f"model {TASK_YOUTUBE_SUMMARY_ALIAS} requires one supported YouTube video URL")
    youtube_urls = [url for url in urls if _extract_video_id(url)]
    if len(youtube_urls) != 1:
        raise HTTPException(status_code=400, detail=f"model {TASK_YOUTUBE_SUMMARY_ALIAS} requires exactly one supported YouTube video URL")
    url = youtube_urls[0]
    video_id = _extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail=f"model {TASK_YOUTUBE_SUMMARY_ALIAS} received an unsupported YouTube URL")
    focus_request = re.sub(r"\s+", " ", _remove_urls(text)).strip()
    return url, video_id, focus_request


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _normalize_segments(fetched: Any) -> list[dict[str, Any]]:
    raw_segments = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
    segments: list[dict[str, Any]] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        start = float(item.get("start") or 0.0)
        duration = float(item.get("duration") or 0.0)
        segments.append(
            {
                "text": re.sub(r"\s+", " ", text),
                "start": start,
                "duration": duration,
                "timestamp": _format_timestamp(start),
            }
        )
    return segments


def _estimate_token_count(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _render_transcript_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(f"[{segment['timestamp']}] {segment['text']}" for segment in segments)


def _fetch_transcript(video_id: str) -> TranscriptFetchResult:
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
    except Exception as exc:  # pragma: no cover - exercised through error mapping
        message = str(exc)
        status = 404 if "No transcripts" in message or "Subtitles are disabled" in message else 502
        raise HTTPException(status_code=status, detail=f"failed to fetch transcript for video {video_id}: {message}") from exc

    def fetch_result(transcript: Any, caption_type: str, was_translated: bool) -> TranscriptFetchResult:
        fetched = transcript.fetch()
        segments = _normalize_segments(fetched)
        transcript_text = _render_transcript_text(segments)
        language = getattr(transcript, "language", "") or "Unknown"
        language_code = getattr(transcript, "language_code", "") or ""
        return TranscriptFetchResult(
            video_id=video_id,
            transcript_text=transcript_text,
            transcript_language=language,
            transcript_language_code=language_code,
            caption_type=caption_type,
            was_translated=was_translated,
            token_estimate=_estimate_token_count(transcript_text),
            segments=segments,
        )

    def try_select(fetcher_name: str, languages: list[str], caption_type: str, translated: bool = False) -> TranscriptFetchResult | None:
        fetcher = getattr(transcript_list, fetcher_name, None)
        if fetcher is None:
            return None
        try:
            transcript = fetcher(languages)
        except Exception:
            return None
        if translated:
            try:
                transcript = transcript.translate("en")
            except Exception:
                return None
        return fetch_result(transcript, caption_type, translated)

    direct_manual = try_select("find_manually_created_transcript", ["en"], "manual", translated=False)
    if direct_manual:
        return direct_manual
    direct_generated = try_select("find_generated_transcript", ["en"], "generated", translated=False)
    if direct_generated:
        return direct_generated

    manual_candidates: list[Any] = []
    generated_candidates: list[Any] = []
    for transcript in transcript_list:
        if getattr(transcript, "is_generated", False):
            generated_candidates.append(transcript)
        else:
            manual_candidates.append(transcript)

    for transcript in manual_candidates:
        if not getattr(transcript, "is_translatable", False):
            continue
        try:
            return fetch_result(transcript.translate("en"), "translated-manual", True)
        except Exception:
            continue
    for transcript in generated_candidates:
        if not getattr(transcript, "is_translatable", False):
            continue
        try:
            return fetch_result(transcript.translate("en"), "translated-generated", True)
        except Exception:
            continue

    raise HTTPException(status_code=404, detail=f"no usable English transcript was available for video {video_id}")


def _split_into_chunks(segments: list[dict[str, Any]], max_tokens: int = CHUNK_TARGET_TOKENS) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_segments: list[dict[str, Any]] = []
    current_tokens = 0
    for segment in segments:
        line = f"[{segment['timestamp']}] {segment['text']}"
        line_tokens = _estimate_token_count(line)
        if current_segments and current_tokens + line_tokens > max_tokens:
            chunks.append(
                {
                    "start_timestamp": current_segments[0]["timestamp"],
                    "end_timestamp": current_segments[-1]["timestamp"],
                    "start_ms": int(round(float(current_segments[0]["start"]) * 1000.0)),
                    "end_ms": int(
                        round(
                            (float(current_segments[-1]["start"]) + float(current_segments[-1]["duration"])) * 1000.0
                        )
                    ),
                    "transcript_text": _render_transcript_text(current_segments),
                    "token_estimate": current_tokens,
                }
            )
            current_segments = []
            current_tokens = 0
        current_segments.append(segment)
        current_tokens += line_tokens
    if current_segments:
        chunks.append(
            {
                "start_timestamp": current_segments[0]["timestamp"],
                "end_timestamp": current_segments[-1]["timestamp"],
                "start_ms": int(round(float(current_segments[0]["start"]) * 1000.0)),
                "end_ms": int(
                    round((float(current_segments[-1]["start"]) + float(current_segments[-1]["duration"])) * 1000.0)
                ),
                "transcript_text": _render_transcript_text(current_segments),
                "token_estimate": current_tokens,
            }
        )
    return chunks


def _memory_api_base() -> str:
    return os.getenv("MEMORY_API_BASE", "http://192.168.1.72:55440").rstrip("/")


def _memory_api_headers(path: str) -> dict[str, str]:
    token = os.getenv("MEMORY_API_BEARER_TOKEN", "").strip()
    if not token:
        return {}
    if path in {"/v1/memory/upsert", "/v1/memory/delete", "/v1/memory/response-map/upsert"}:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _youtube_document_id(video_id: str) -> str:
    return f"youtube:{video_id}"


async def _post_memory_api(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{_memory_api_base()}{path}", json=payload, headers=_memory_api_headers(path))
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, dict) else {}


async def _upsert_transcript_document(transcript: TranscriptFetchResult) -> str:
    document_id = _youtube_document_id(transcript.video_id)
    payload = {
        "documents": [
            {
                "document_id": document_id,
                "source_type": "youtube",
                "source": "youtube",
                "source_thread_id": transcript.video_id,
                "source_message_id": transcript.video_id,
                "title": transcript.video_id,
                "uri": f"https://youtu.be/{transcript.video_id}",
                "metadata": {
                    "caption_type": transcript.caption_type,
                    "transcript_language": transcript.transcript_language,
                    "transcript_language_code": transcript.transcript_language_code,
                    "was_translated": transcript.was_translated,
                },
                "chunks": [
                    {
                        "chunk_index": idx,
                        "text": chunk["transcript_text"],
                        "timestamp_label": chunk["start_timestamp"],
                        "start_ms": chunk["start_ms"],
                        "end_ms": chunk["end_ms"],
                        "metadata": {
                            "caption_type": transcript.caption_type,
                            "transcript_language": transcript.transcript_language,
                            "transcript_language_code": transcript.transcript_language_code,
                            "was_translated": transcript.was_translated,
                        },
                    }
                    for idx, chunk in enumerate(_split_into_chunks(transcript.segments))
                ],
            }
        ]
    }
    await _post_memory_api("/v1/memory/upsert", payload)
    return document_id


async def _upsert_response_mapping(response_id: str, document_id: str, summary_mode: str) -> None:
    await _post_memory_api(
        "/v1/memory/response-map/upsert",
        {
            "response_id": response_id,
            "document_id": document_id,
            "source_type": "youtube",
            "summary_mode": summary_mode,
        },
    )


async def _resolve_response_mapping(previous_response_id: str) -> dict[str, Any] | None:
    try:
        return await _post_memory_api("/v1/memory/response-map/resolve", {"response_id": previous_response_id})
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise


async def _search_document(question: str, document_id: str) -> list[dict[str, Any]]:
    body = await _post_memory_api(
        "/v1/memory/search",
        {
            "query": question,
            "profile": "balanced",
            "document_id": document_id,
            "source_type": "youtube",
            "render_citations": False,
        },
    )
    hits = body.get("hits")
    return list(hits) if isinstance(hits, list) else []


def _build_followup_retrieval_messages(question: str, hits: list[dict[str, Any]]) -> list[dict[str, str]]:
    excerpts: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        if not isinstance(hit, dict):
            continue
        text = str(hit.get("text") or "").strip()
        if not text:
            continue
        spans = hit.get("spans") or {}
        excerpts.append(
            f"Excerpt {idx}\nTimestamp: {spans.get('timestamp_label') or ''}\nText:\n{text}"
        )
    return [
        {
            "role": "system",
            "content": (
                "Answer the question using only the retrieved transcript excerpts. "
                "If the excerpts do not support a confident answer, say that directly. "
                "Do not render citations unless the user explicitly asks for them."
            ),
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nRetrieved transcript excerpts:\n\n" + "\n\n".join(excerpts),
        },
    ]


def _extract_responses_text(response: Any) -> str | None:
    body = response.model_dump() if hasattr(response, "model_dump") else response
    if not isinstance(body, dict):
        return None
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        text = _coerce_text(item.get("content")).strip()
        if text:
            return text
    return None


def _extract_chat_text(response: Any) -> str | None:
    body = response.model_dump() if hasattr(response, "model_dump") else response
    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return None
    text = _coerce_text(message.get("content")).strip()
    return text or None


def _response_to_dict(response: Any) -> dict[str, Any] | None:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    return response if isinstance(response, dict) else None


def _restore_response_type(template: Any, body: dict[str, Any]) -> Any:
    model_validate = getattr(getattr(template, "__class__", None), "model_validate", None)
    if callable(model_validate):
        try:
            return model_validate(body)
        except Exception:
            return body
    return body


def _set_responses_text(response: Any, content: str) -> Any:
    body = _response_to_dict(response)
    if not body:
        return response
    body["output"] = [
        {
            "id": body.get("id", "resp_youtube_summary"),
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": content, "annotations": []}],
        }
    ]
    body["output_text"] = content
    body.pop("reasoning", None)
    return _restore_response_type(response, body)


def _set_chat_text(response: Any, content: str) -> Any:
    body = _response_to_dict(response)
    if not body:
        return response
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return response
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return response
    message["content"] = content
    message.pop("reasoning", None)
    message.pop("reasoning_content", None)
    message.pop("provider_specific_fields", None)
    return _restore_response_type(response, body)


def _build_chunk_summary_messages(chunk: dict[str, Any], focus_request: str) -> list[dict[str, str]]:
    focus_line = focus_request or "None"
    return [
        {
            "role": "system",
            "content": (
                "You are summarizing one chunk of a YouTube transcript for later synthesis. "
                "Capture the concrete content faithfully. Keep timestamps when they matter. "
                "Do not add filler, intro, or outro."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Focus request: {focus_line}\n"
                f"Chunk window: {chunk['start_timestamp']} to {chunk['end_timestamp']}\n\n"
                "Return a compact chunk summary with:\n"
                "- 3-6 key points\n"
                "- notable claims or examples\n"
                "- sparse timestamps only when useful\n\n"
                f"Transcript chunk:\n{chunk['transcript_text']}"
            ),
        },
    ]


def _build_final_synthesis_messages(
    transcript: TranscriptFetchResult,
    focus_request: str,
    chunk_summaries: list[str],
) -> list[dict[str, str]]:
    joined_summaries = "\n\n".join(
        f"Chunk {index + 1} summary:\n{summary}" for index, summary in enumerate(chunk_summaries)
    )
    focus_line = focus_request or "None"
    return [
        {
            "role": "system",
            "content": (
                "You are creating a comprehensive summary of a YouTube video from chunk summaries. "
                "Write readable markdown with adaptive sections. Start with a compact metadata line "
                "for the video id, transcript language, and caption type. Include a concise overview, "
                "key takeaways, and any additional sections that best fit the content. Use sparse timestamps only."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Video ID: {transcript.video_id}\n"
                f"Transcript language: {transcript.transcript_language}\n"
                f"Caption type: {transcript.caption_type}\n"
                f"Focus request: {focus_line}\n\n"
                "Synthesize these chunk summaries into one comprehensive summary. "
                "Keep the structure flexible and fit it to the actual content.\n\n"
                f"{joined_summaries}"
            ),
        },
    ]


async def _post_responses(api_base: str, api_key: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "dummy":
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{api_base}/responses", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def _run_chunked_summary(data: dict[str, Any], transcript: TranscriptFetchResult) -> dict[str, Any]:
    api_base = data.get("api_base") or os.getenv("LLMSTER_DEEP_API_BASE")
    provider_model = data.get("model")
    if _is_target_model(provider_model):
        provider_model = None
    provider_model = provider_model or os.getenv("LLMSTER_DEEP_MODEL")
    if not isinstance(api_base, str) or not api_base:
        raise HTTPException(status_code=502, detail="task-youtube-summary chunking requires provider api_base")
    if not isinstance(provider_model, str) or not provider_model:
        raise HTTPException(status_code=502, detail="task-youtube-summary chunking requires provider model")
    provider_model = _strip_provider_prefix(provider_model)
    api_key = data.get("api_key") if isinstance(data.get("api_key"), str) else None
    focus_request = str(data.get("_youtube_summary_focus_request") or "")

    chunk_summaries: list[str] = []
    for chunk in _split_into_chunks(transcript.segments):
        body = await _post_responses(
            api_base,
            api_key,
            {
                "model": provider_model,
                "input": _build_chunk_summary_messages(chunk, focus_request),
                "reasoning": {"effort": "low"},
                "temperature": 0.0,
                "stream": False,
                "max_output_tokens": CHUNK_SUMMARY_MAX_OUTPUT_TOKENS,
            },
        )
        text = _extract_responses_text(body)
        if not text:
            raise HTTPException(status_code=502, detail="task-youtube-summary chunk summarization returned empty output")
        chunk_summaries.append(text)

    final_body = await _post_responses(
        api_base,
        api_key,
        {
            "model": provider_model,
            "input": _build_final_synthesis_messages(transcript, focus_request, chunk_summaries),
            "reasoning": {"effort": "low"},
            "temperature": 0.0,
            "stream": False,
            "max_output_tokens": FINAL_SUMMARY_MAX_OUTPUT_TOKENS,
        },
    )
    return final_body


class YouTubeSummaryGuardrail(CustomGuardrail):
    def __init__(self, guardrail_name: str, event_hook: str, default_on: bool, **kwargs):
        super().__init__(
            guardrail_name=guardrail_name,
            supported_event_hooks=[GuardrailEventHooks.pre_call, GuardrailEventHooks.post_call],
            event_hook=event_hook,
            default_on=default_on,
            **kwargs,
        )

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> dict:
        if not _is_target_model(data.get("model")):
            return data

        previous_response_id = data.get("previous_response_id")
        latest_user_text = (
            _extract_latest_user_text_from_input(data.get("input"))
            if call_type in {"responses", "aresponses"}
            else _extract_latest_user_text_from_messages(data.get("messages"))
        )
        if isinstance(previous_response_id, str) and previous_response_id.strip():
            mapping = await _resolve_response_mapping(previous_response_id)
            if mapping and latest_user_text:
                document_id = str(mapping.get("document_id") or "").strip()
                hits = await _search_document(latest_user_text, document_id)
                messages = _build_followup_retrieval_messages(latest_user_text, hits)
                data.pop("previous_response_id", None)
                if call_type in {"responses", "aresponses"}:
                    data["input"] = messages
                    data.pop("messages", None)
                    current_budget = data.get("max_output_tokens")
                    if not isinstance(current_budget, int) or current_budget < MIN_RESPONSE_OUTPUT_TOKENS:
                        data["max_output_tokens"] = MIN_RESPONSE_OUTPUT_TOKENS
                else:
                    data["messages"] = messages
                    data.pop("input", None)
                    current_budget = data.get("max_tokens")
                    if not isinstance(current_budget, int) or current_budget < MIN_CHAT_OUTPUT_TOKENS:
                        data["max_tokens"] = MIN_CHAT_OUTPUT_TOKENS
                data["stream"] = False
                logger.info(
                    "youtube-summary retrieval-followup alias=%s previous_response_id=%s document_id=%s hits=%s",
                    data.get("model"),
                    previous_response_id,
                    document_id,
                    len(hits),
                )
                return data
            logger.info("youtube-summary follow-up alias=%s previous_response_id=%s", data.get("model"), previous_response_id)
            return data

        if not latest_user_text:
            raise HTTPException(status_code=400, detail=f"model {TASK_YOUTUBE_SUMMARY_ALIAS} requires a YouTube URL on the first turn")

        _, video_id, focus_request = _extract_url_and_focus_request(latest_user_text)
        transcript = _fetch_transcript(video_id)
        document_id = _youtube_document_id(transcript.video_id)

        data["_youtube_summary_initial"] = True
        data["_youtube_summary_focus_request"] = focus_request
        data["_youtube_summary_video_id"] = transcript.video_id
        data["_youtube_summary_transcript_language"] = transcript.transcript_language
        data["_youtube_summary_caption_type"] = transcript.caption_type
        data["_youtube_summary_chunked"] = transcript.token_estimate > SINGLE_PASS_TRANSCRIPT_TOKENS
        data["_youtube_summary_transcript_meta"] = {
            "video_id": transcript.video_id,
            "transcript_language": transcript.transcript_language,
            "transcript_language_code": transcript.transcript_language_code,
            "caption_type": transcript.caption_type,
            "was_translated": transcript.was_translated,
            "token_estimate": transcript.token_estimate,
            "segments": transcript.segments,
            "document_id": document_id,
        }
        with _LOCK:
            _REQUEST_CONTEXTS[id(data)] = {
                "chunked": data["_youtube_summary_chunked"],
                "focus_request": focus_request,
                "transcript_meta": dict(data["_youtube_summary_transcript_meta"]),
                "model": data.get("model"),
                "api_base": data.get("api_base"),
                "api_key": data.get("api_key"),
            }

        await _upsert_transcript_document(transcript)

        if call_type in {"responses", "aresponses"}:
            current_budget = data.get("max_output_tokens")
            if not isinstance(current_budget, int) or current_budget < MIN_RESPONSE_OUTPUT_TOKENS:
                data["max_output_tokens"] = MIN_RESPONSE_OUTPUT_TOKENS
        else:
            current_budget = data.get("max_tokens")
            if not isinstance(current_budget, int) or current_budget < MIN_CHAT_OUTPUT_TOKENS:
                data["max_tokens"] = MIN_CHAT_OUTPUT_TOKENS

        if data["_youtube_summary_chunked"]:
            placeholder = "youtube-summary-chunked-placeholder"
            if call_type in {"responses", "aresponses"}:
                data["input"] = [{"role": "user", "content": f"Reply with exactly: {placeholder}"}]
                data.pop("messages", None)
                data["max_output_tokens"] = 64
            else:
                data["messages"] = [{"role": "user", "content": f"Reply with exactly: {placeholder}"}]
                data.pop("input", None)
                data["max_tokens"] = 64
            logger.info(
                "youtube-summary pre_call alias=%s video_id=%s transcript_tokens=%s chunked=true",
                data.get("model"),
                transcript.video_id,
                transcript.token_estimate,
            )
            return data

        prompt_variables = {
            "video_id": transcript.video_id,
            "transcript_language": transcript.transcript_language,
            "caption_type": transcript.caption_type,
            "focus_request": focus_request or "None",
            "transcript_text": transcript.transcript_text,
        }
        data["prompt_id"] = PROMPT_ID
        data["prompt_variables"] = prompt_variables
        data["stream"] = False
        logger.info(
            "youtube-summary pre_call alias=%s video_id=%s transcript_tokens=%s chunked=false",
            data.get("model"),
            transcript.video_id,
            transcript.token_estimate,
        )
        return data

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        with _LOCK:
            request_context = _REQUEST_CONTEXTS.pop(id(data), None)

        if not _is_target_model(data.get("model")) and not request_context:
            return response

        chunked = bool(data.pop("_youtube_summary_chunked", False))
        transcript_meta = data.pop("_youtube_summary_transcript_meta", None)
        if request_context:
            chunked = bool(request_context.get("chunked", chunked))
            if transcript_meta is None:
                transcript_meta = request_context.get("transcript_meta")
            if "_youtube_summary_focus_request" not in data and request_context.get("focus_request") is not None:
                data["_youtube_summary_focus_request"] = request_context.get("focus_request")
            if not data.get("api_base") and request_context.get("api_base"):
                data["api_base"] = request_context.get("api_base")
            if not data.get("api_key") and request_context.get("api_key"):
                data["api_key"] = request_context.get("api_key")
            if _is_target_model(data.get("model")) and request_context.get("model"):
                data["model"] = request_context.get("model")
        response_body = _response_to_dict(response)

        if chunked and isinstance(transcript_meta, dict):
            transcript = TranscriptFetchResult(
                video_id=str(transcript_meta["video_id"]),
                transcript_text=_render_transcript_text(list(transcript_meta["segments"])),
                transcript_language=str(transcript_meta["transcript_language"]),
                transcript_language_code=str(transcript_meta["transcript_language_code"]),
                caption_type=str(transcript_meta["caption_type"]),
                was_translated=bool(transcript_meta["was_translated"]),
                token_estimate=int(transcript_meta["token_estimate"]),
                segments=list(transcript_meta["segments"]),
            )
            final_response = await _run_chunked_summary(data, transcript)
            text = _extract_responses_text(final_response)
            if not text:
                raise HTTPException(status_code=502, detail="task-youtube-summary final synthesis returned empty output")
            if response_body and response_body.get("object") == "response":
                rewritten = _set_responses_text(response, text)
            else:
                rewritten = _set_chat_text(response, text)
            rewritten_body = _response_to_dict(rewritten)
            response_id = str(rewritten_body.get("id") or response_body.get("id") or "").strip()
            document_id = str(transcript_meta.get("document_id") or "").strip()
            if response_id and document_id:
                await _upsert_response_mapping(response_id, document_id, "indexed_long")
            return rewritten

        if response_body and response_body.get("object") == "response":
            text = _extract_responses_text(response)
            if not text:
                return response
            rewritten = _set_responses_text(response, text)
            rewritten_body = _response_to_dict(rewritten)
            response_id = str(rewritten_body.get("id") or response_body.get("id") or "").strip()
            document_id = str((transcript_meta or {}).get("document_id") or "").strip() if isinstance(transcript_meta, dict) else ""
            if response_id and document_id:
                await _upsert_response_mapping(response_id, document_id, "direct_short")
            return rewritten

        text = _extract_chat_text(response)
        if not text:
            return response
        rewritten = _set_chat_text(response, text)
        rewritten_body = _response_to_dict(rewritten)
        response_id = str(rewritten_body.get("id") or response_body.get("id") or "").strip()
        document_id = str((transcript_meta or {}).get("document_id") or "").strip() if isinstance(transcript_meta, dict) else ""
        if response_id and document_id:
            await _upsert_response_mapping(
                response_id,
                document_id,
                "indexed_long" if chunked else "direct_short",
            )
        return rewritten
