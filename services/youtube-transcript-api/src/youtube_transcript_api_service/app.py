from __future__ import annotations

import re
import time
import uuid
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .transcripts import TranscriptError, fetch_transcript

MODEL_ID = "youtube-transcript"
_URL_RE = re.compile(r"https?://[^\s<>()\[\]{}]+", re.IGNORECASE)


class ChatMessage(BaseModel):
    role: str
    content: Any = ""


class ChatCompletionRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool = False


def _coerce_content(content: Any) -> str:
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
    return str(content)


def _extract_latest_user_text(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            text = _coerce_content(message.content).strip()
            if text:
                return text
    return ""


def _extract_single_url(text: str) -> str:
    urls = [match.group(0).rstrip("),.;!?:]}") for match in _URL_RE.finditer(text)]
    if len(urls) != 1:
        raise TranscriptError("invalid_request", "request must contain exactly one YouTube URL", 400)
    return urls[0]


def _usage_for(text: str) -> dict[str, int]:
    tokens = max(1, len(text) // 4)
    return {"prompt_tokens": 0, "completion_tokens": tokens, "total_tokens": tokens}


def _chat_response(content: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-yt-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": _usage_for(content),
    }


def _error_response(exc: TranscriptError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "type": exc.code,
                "code": exc.code,
            }
        },
    )


def create_app() -> FastAPI:
    api = FastAPI(title="YouTube Transcript API", version="0.1.0")

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/v1/models")
    def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [{"id": MODEL_ID, "object": "model", "created": 0, "owned_by": "homelab-llm"}],
        }

    @api.post("/v1/chat/completions")
    async def chat_completions(payload: ChatCompletionRequest) -> JSONResponse:
        if payload.stream:
            return _error_response(TranscriptError("unsupported_request", "streaming is not supported", 400))
        text = _extract_latest_user_text(payload.messages)
        try:
            url = _extract_single_url(text)
            document = fetch_transcript(url)
        except TranscriptError as exc:
            return _error_response(exc)
        response = _chat_response(document.transcript_text, payload.model or MODEL_ID)
        response["transcript"] = document.model_payload()
        return JSONResponse(response)

    return api


app = create_app()
