from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


ADAPTER_MODEL = "openai/gpt-5.3-codex"
UNSUPPORTED_REQUEST_KEYS = {
    "functions",
    "parallel_tool_calls",
    "response_format",
    "tool_choice",
    "tools",
}


@dataclass(frozen=True)
class AdapterConfig:
    ccproxy_api_base: str
    ccproxy_auth_token: str | None
    deep_api_base: str
    deep_model: str
    deep_api_key: str

    @classmethod
    def from_env(cls) -> "AdapterConfig":
        ccproxy_api_base = os.environ.get("CCPROXY_API_BASE", "http://127.0.0.1:4010/codex/v1").rstrip("/")
        deep_api_base = os.environ.get("LLMSTER_DEEP_API_BASE", "").rstrip("/")
        deep_model = os.environ.get("LLMSTER_DEEP_MODEL", "")
        if not deep_api_base or not deep_model:
            raise RuntimeError("LLMSTER_DEEP_API_BASE and LLMSTER_DEEP_MODEL are required")
        return cls(
            ccproxy_api_base=ccproxy_api_base,
            ccproxy_auth_token=os.environ.get("CCPROXY_AUTH_TOKEN"),
            deep_api_base=deep_api_base,
            deep_model=deep_model,
            deep_api_key=os.environ.get("LLMSTER_DEEP_API_KEY", "dummy"),
        )


def _utc_ts() -> int:
    return int(time.time())


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
        if isinstance(text, dict):
            return _flatten_text(text.get("value"))
        if value.get("type") in {"text", "input_text", "output_text"}:
            return _flatten_text(value.get("text") or value.get("value"))
        if "content" in value:
            return _flatten_text(value.get("content"))
        if "input" in value:
            return _flatten_text(value.get("input"))
        return ""
    return str(value)


def _extract_chat_text(payload: dict[str, Any]) -> str:
    for choice in payload.get("choices", []):
        message = choice.get("message", {})
        text = _flatten_text(message.get("content"))
        if text.strip():
            return text.strip()
    return ""


def _extract_responses_text(payload: dict[str, Any]) -> str:
    direct = _flatten_text(payload.get("output_text"))
    if direct.strip():
        return direct.strip()
    output = payload.get("output", [])
    text = _flatten_text(output)
    if text.strip():
        return text.strip()
    return ""


def _coerce_messages(source: dict[str, Any]) -> list[dict[str, Any]]:
    messages = source.get("messages")
    if isinstance(messages, list) and messages:
        return messages
    prompt = _flatten_text(source.get("input"))
    if prompt.strip():
        return [{"role": "user", "content": prompt.strip()}]
    raise HTTPException(status_code=400, detail="chatgpt-5 requires text input in messages or input")


def _sanitize_payload(source: dict[str, Any], endpoint: str) -> dict[str, Any]:
    payload = dict(source)
    payload["model"] = ADAPTER_MODEL
    payload["stream"] = False
    payload["temperature"] = 0.0
    for key in UNSUPPORTED_REQUEST_KEYS:
        payload.pop(key, None)
    if endpoint == "responses":
        payload["input"] = _coerce_messages(source)
        payload.pop("messages", None)
    else:
        payload["messages"] = _coerce_messages(source)
        payload.pop("input", None)
    return payload


def _response_usage(source: dict[str, Any] | None) -> dict[str, int]:
    usage = source or {}
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _build_chat_response(text: str, usage: dict[str, Any] | None, *, model: str = ADAPTER_MODEL) -> dict[str, Any]:
    return {
        "id": f"chatcmpl_{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": _utc_ts(),
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": text},
            }
        ],
        "usage": _response_usage(usage),
    }


def _build_responses_response(text: str, usage: dict[str, Any] | None) -> dict[str, Any]:
    usage_data = _response_usage(usage)
    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": _utc_ts(),
        "status": "completed",
        "model": ADAPTER_MODEL,
        "output": [
            {
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "output_text": text,
        "usage": {
            "input_tokens": usage_data["prompt_tokens"],
            "output_tokens": usage_data["completion_tokens"],
            "total_tokens": usage_data["total_tokens"],
        },
    }


class ChatGPT5Adapter:
    def __init__(self, config: AdapterConfig):
        self._config = config

    def _deep_provider_model(self) -> str:
        return self._config.deep_model.removeprefix("openai/")

    def _headers(self, *, auth_token: str | None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    async def _post_json(self, base_url: str, path: str, payload: dict[str, Any], *, auth_token: str | None) -> tuple[int, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(f"{base_url}{path}", headers=self._headers(auth_token=auth_token), json=payload)
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"detail": response.text}
        return response.status_code, data

    async def _call_ccproxy_chat(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return await self._post_json(
            self._config.ccproxy_api_base,
            "/chat/completions",
            payload,
            auth_token=self._config.ccproxy_auth_token,
        )

    async def _call_ccproxy_responses(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return await self._post_json(
            self._config.ccproxy_api_base,
            "/responses",
            payload,
            auth_token=self._config.ccproxy_auth_token,
        )

    async def _call_deep_chat(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        deep_payload = {
            "model": self._deep_provider_model(),
            "messages": _coerce_messages(payload),
            "stream": False,
            "temperature": 0.0,
        }
        if "max_tokens" in payload:
            deep_payload["max_tokens"] = payload["max_tokens"]
        return await self._post_json(
            self._config.deep_api_base,
            "/chat/completions",
            deep_payload,
            auth_token=self._config.deep_api_key,
        )

    async def handle_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        chat_payload = _sanitize_payload(payload, endpoint="chat")
        status_code, response_payload = await self._call_ccproxy_chat(chat_payload)
        text = _extract_chat_text(response_payload) if status_code < 500 else ""
        if text:
            return response_payload

        responses_status, responses_payload = await self._call_ccproxy_responses(_sanitize_payload(payload, endpoint="responses"))
        text = _extract_responses_text(responses_payload) if responses_status < 500 else ""
        if text:
            return _build_chat_response(text, responses_payload.get("usage"))

        deep_status, deep_payload = await self._call_deep_chat(chat_payload)
        text = _extract_chat_text(deep_payload) if deep_status < 500 else ""
        if text:
            return _build_chat_response(text, deep_payload.get("usage"), model=ADAPTER_MODEL)

        raise HTTPException(
            status_code=502,
            detail="chatgpt-5 adapter could not extract assistant text from ccproxy-api or deep fallback",
        )

    async def handle_responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        responses_payload = _sanitize_payload(payload, endpoint="responses")
        status_code, response_payload = await self._call_ccproxy_responses(responses_payload)
        text = _extract_responses_text(response_payload) if status_code < 500 else ""
        if text:
            return _build_responses_response(text, response_payload.get("usage"))

        deep_status, deep_payload = await self._call_deep_chat(_sanitize_payload(payload, endpoint="chat"))
        text = _extract_chat_text(deep_payload) if deep_status < 500 else ""
        if text:
            return _build_responses_response(text, deep_payload.get("usage"))

        raise HTTPException(
            status_code=502,
            detail="chatgpt-5 adapter could not build a valid /v1/responses payload",
        )

app = FastAPI(title="chatgpt-5 adapter", version="0.1.0")


def _get_adapter() -> ChatGPT5Adapter:
    adapter = getattr(app.state, "adapter", None)
    if adapter is None:
        adapter = ChatGPT5Adapter(AdapterConfig.from_env())
        app.state.adapter = adapter
    return adapter


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def models() -> dict[str, list[dict[str, str]]]:
    return {
        "data": [
            {
                "id": ADAPTER_MODEL,
                "object": "model",
                "owned_by": "chatgpt-5-adapter",
            }
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    payload = await request.json()
    body = await _get_adapter().handle_chat_completions(payload)
    return JSONResponse(body)


@app.post("/v1/responses")
async def responses(request: Request) -> JSONResponse:
    payload = await request.json()
    body = await _get_adapter().handle_responses(payload)
    return JSONResponse(body)
