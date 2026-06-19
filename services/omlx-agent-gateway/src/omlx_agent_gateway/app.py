from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Mapping

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from homelab_observability import (
    current_trace_id,
    inject_trace_headers,
    instrument_fastapi_app,
    set_llm_content_attributes,
    setup_tracing,
    start_as_current_span,
)
from opentelemetry.trace import SpanKind

from .settings import Settings, load_settings

setup_tracing(
    service_name="omlx-agent-gateway",
    service_version="0.1.0",
    resource_attributes={"host.name": "mini", "homelab.plane": "gateway"},
)


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


def _upstream_headers(settings: Settings, *, request_id: str | None = None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "close",
    }
    if request_id:
        headers["X-Request-ID"] = request_id
    if settings.backend_api_key:
        headers["Authorization"] = f"Bearer {settings.backend_api_key}"
    return headers


def _proxy_json(
    settings: Settings,
    *,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    request_id: str,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    with start_as_current_span(
        "omlx_agent_gateway.upstream.chat",
        kind=SpanKind.CLIENT,
        attributes={
            "http.request.method": method,
            "url.full": f"{settings.backend_base_url.rstrip('/')}{path}",
            "server.address": settings.backend_base_url,
            "homelab.request_id": request_id,
            "gen_ai.request.model": str(payload.get("model", "")) if isinstance(payload, Mapping) else "",
        },
    ) as span:
        if isinstance(payload, Mapping):
            set_llm_content_attributes(span, prefix="gen_ai.request", messages=payload.get("messages"))
        request = urllib.request.Request(
            f"{settings.backend_base_url.rstrip('/')}{path}",
            data=body,
            headers=inject_trace_headers(_upstream_headers(settings, request_id=request_id)),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.timeout_seconds) as response:
                raw = response.read()
                status = response.status
                span.set_attribute("http.response.status_code", status)
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            span.set_attribute("http.response.status_code", exc.code)
            try:
                parsed_error = json.loads(raw_body)
            except json.JSONDecodeError:
                parsed_error = {"error": {"message": raw_body[:500], "type": "upstream_http_error"}}
            return exc.code, parsed_error
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            span.set_attribute("error.type", "upstream_transport_error")
            return 502, {"error": {"message": f"upstream transport failed: {exc}", "type": "upstream_transport_error"}}

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            span.set_attribute("error.type", "upstream_parse_error")
            return 502, {"error": {"message": raw[:500].decode("utf-8", errors="replace"), "type": "upstream_parse_error"}}
        if not isinstance(parsed, dict):
            span.set_attribute("error.type", "upstream_parse_error")
            return 502, {"error": {"message": "upstream returned non-object JSON", "type": "upstream_parse_error"}}
        set_llm_content_attributes(span, prefix="gen_ai.response", response=_extract_response_text(parsed))
        return status, parsed


def _proxy_stream(settings: Settings, *, path: str, payload: dict[str, Any], request_id: str) -> JSONResponse | StreamingResponse:
    with start_as_current_span(
        "omlx_agent_gateway.upstream.chat.stream",
        kind=SpanKind.CLIENT,
        attributes={
            "http.request.method": "POST",
            "url.full": f"{settings.backend_base_url.rstrip('/')}{path}",
            "homelab.request_id": request_id,
            "gen_ai.request.model": str(payload.get("model", "")),
            "gen_ai.request.stream": True,
        },
    ) as span:
        request = urllib.request.Request(
            f"{settings.backend_base_url.rstrip('/')}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=inject_trace_headers(_upstream_headers(settings, request_id=request_id)),
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request, timeout=settings.timeout_seconds)
            span.set_attribute("http.response.status_code", response.status)
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            span.set_attribute("http.response.status_code", exc.code)
            try:
                parsed_error = json.loads(raw_body)
            except json.JSONDecodeError:
                parsed_error = {"error": {"message": raw_body[:500], "type": "upstream_http_error"}}
            return JSONResponse(status_code=exc.code, content=parsed_error)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            span.set_attribute("error.type", "upstream_transport_error")
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


def _response_headers(request_id: str) -> dict[str, str]:
    headers = {"X-Request-ID": request_id}
    trace_id = current_trace_id()
    if trace_id:
        headers["X-Trace-ID"] = trace_id
    return headers


def _extract_response_text(body: Mapping[str, Any]) -> str:
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping):
                content = message.get("content")
                if isinstance(content, str):
                    return content
    return ""


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
    async def chat_completions(request: Request, authorization: str | None = Header(default=None)) -> Any:
        settings = load_settings()
        _require_auth(settings, authorization)
        request_id = request.headers.get("x-request-id") or f"omlx-gw-{uuid.uuid4().hex[:12]}"
        payload = await request.json()
        if not isinstance(payload, dict):
            return _error_response("request body must be a JSON object", status_code=400, error_type="invalid_request_error")
        normalized = _normalize_chat_payload(settings, payload)
        if isinstance(normalized, JSONResponse):
            return normalized
        if normalized.pop("_omlx_agent_gateway_test_response", None):
            return JSONResponse(_local_chat_response(settings, "gateway-ok"), headers=_response_headers(request_id))
        if normalized.get("stream"):
            response = _proxy_stream(settings, path="/chat/completions", payload=normalized, request_id=request_id)
            response.headers.update(_response_headers(request_id))
            return response
        status, body = _proxy_json(settings, method="POST", path="/chat/completions", payload=normalized, request_id=request_id)
        if body.get("model") == settings.backend_model:
            body = dict(body)
            body["model"] = settings.public_model_id
        return JSONResponse(status_code=status, content=body, headers=_response_headers(request_id))

    instrument_fastapi_app(api, excluded_urls="/health")
    return api


app = create_app()


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
