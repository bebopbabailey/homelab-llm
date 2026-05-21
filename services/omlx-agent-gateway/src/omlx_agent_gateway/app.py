from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .settings import Settings, load_settings


def _error_response(message: str, *, status_code: int, error_type: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type}},
    )


def _require_auth(settings: Settings, authorization: str | None) -> None:
    if not settings.auth_token:
        return
    if authorization != f"Bearer {settings.auth_token}":
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "invalid bearer token", "type": "authentication_error"}},
        )


def _model_info_payload(settings: Settings) -> dict[str, Any]:
    return {
        "data": [
            {
                "model_name": settings.public_model_id,
                "litellm_params": {
                    "model": f"openai/{settings.backend_model}",
                    "api_base": settings.backend_base_url,
                    "max_tokens": settings.max_output_tokens,
                },
                "model_info": {
                    "key": settings.public_model_id,
                    "mode": "chat",
                    "supports_system_messages": True,
                    "supports_function_calling": True,
                    "supports_parallel_function_calling": False,
                    "supports_response_schema": False,
                    "supports_vision": False,
                    "max_input_tokens": settings.max_input_tokens,
                    "max_output_tokens": settings.max_output_tokens,
                    "litellm_provider": "openai",
                },
            }
        ]
    }


def _models_payload(settings: Settings) -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": settings.public_model_id,
                "object": "model",
                "created": 0,
                "owned_by": "omlx-agent-gateway",
            }
        ],
    }


def _upstream_headers(settings: Settings) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Connection": "close"}
    if settings.backend_api_key:
        headers["Authorization"] = f"Bearer {settings.backend_api_key}"
    return headers


def _proxy_json(settings: Settings, *, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{settings.backend_base_url.rstrip('/')}{path}",
        data=body,
        headers=_upstream_headers(settings),
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout_seconds) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_error = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed_error = {"error": {"message": raw_body[:500], "type": "upstream_http_error"}}
        return exc.code, parsed_error
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return 502, {"error": {"message": f"upstream transport failed: {exc}", "type": "upstream_transport_error"}}

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return 502, {"error": {"message": raw[:500].decode("utf-8", errors="replace"), "type": "upstream_parse_error"}}
    if not isinstance(parsed, dict):
        return 502, {"error": {"message": "upstream returned non-object JSON", "type": "upstream_parse_error"}}
    return status, parsed


def _proxy_stream(settings: Settings, *, path: str, payload: dict[str, Any]) -> JSONResponse | StreamingResponse:
    request = urllib.request.Request(
        f"{settings.backend_base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=_upstream_headers(settings),
        method="POST",
    )
    try:
        response = urllib.request.urlopen(request, timeout=settings.timeout_seconds)
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_error = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed_error = {"error": {"message": raw_body[:500], "type": "upstream_http_error"}}
        return JSONResponse(status_code=exc.code, content=parsed_error)
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return _error_response(f"upstream transport failed: {exc}", status_code=502, error_type="upstream_transport_error")

    def chunks():
        with response:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        chunks(),
        status_code=response.status,
        media_type=response.headers.get_content_type() or "text/event-stream",
    )


def _normalize_chat_payload(settings: Settings, payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    model = payload.get("model")
    if model not in {settings.public_model_id, settings.backend_model}:
        return _error_response(f"unknown model: {model!r}", status_code=404, error_type="not_found_error")
    normalized = dict(payload)
    normalized["model"] = settings.backend_model
    return normalized


def _local_chat_response(settings: Settings, content: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-omlx-gateway-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": settings.public_model_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def create_app() -> FastAPI:
    api = FastAPI(title="oMLX Agent Gateway", version="0.1.0")

    @api.get("/health")
    def health() -> dict[str, Any]:
        settings = load_settings()
        return {
            "status": "ok",
            "model": settings.public_model_id,
            "backend_base_url": settings.backend_base_url,
            "backend_model": settings.backend_model,
            "bind": f"{settings.host}:{settings.port}",
        }

    @api.get("/v1/models")
    def models(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        settings = load_settings()
        _require_auth(settings, authorization)
        return _models_payload(settings)

    @api.get("/v1/model/info")
    def model_info(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        settings = load_settings()
        _require_auth(settings, authorization)
        return _model_info_payload(settings)

    @api.post("/v1/chat/completions")
    async def chat_completions(request: Request, authorization: str | None = Header(default=None)) -> JSONResponse:
        settings = load_settings()
        _require_auth(settings, authorization)
        payload = await request.json()
        if not isinstance(payload, dict):
            return _error_response("request body must be a JSON object", status_code=400, error_type="invalid_request_error")
        normalized = _normalize_chat_payload(settings, payload)
        if isinstance(normalized, JSONResponse):
            return normalized
        if normalized.pop("_omlx_agent_gateway_test_response", None):
            return JSONResponse(_local_chat_response(settings, "gateway-ok"))
        if normalized.get("stream"):
            return _proxy_stream(settings, path="/chat/completions", payload=normalized)
        status, body = _proxy_json(settings, method="POST", path="/chat/completions", payload=normalized)
        if body.get("model") == settings.backend_model:
            body = dict(body)
            body["model"] = settings.public_model_id
        return JSONResponse(status_code=status, content=body)

    return api


app = create_app()


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
