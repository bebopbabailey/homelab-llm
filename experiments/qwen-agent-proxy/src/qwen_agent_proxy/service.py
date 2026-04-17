from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from .adapter_core import QWEN_AGENT_INSTALL_SPEC, QwenAgentAdapter, load_qwen_agent
from .settings import QwenAgentProxySettings, load_settings


app = FastAPI(title="qwen-agent-proxy", version="0.1.0")


def _error(message: str, *, status_code: int = 400, error_type: str = "invalid_request_error") -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"message": message, "type": error_type}})


def _require_auth(settings: QwenAgentProxySettings, authorization: str | None) -> None:
    if not settings.auth_token:
        raise _error("qwen-agent-proxy auth token is not configured", status_code=500, error_type="server_error")
    expected = f"Bearer {settings.auth_token}"
    if authorization != expected:
        raise _error("invalid bearer token", status_code=401, error_type="authentication_error")


def _parse_tool_choice(tool_choice: Any) -> tuple[bool, list[str] | None, bool]:
    if tool_choice is None or tool_choice == "auto":
        return False, None, True
    if tool_choice == "required":
        return True, None, True
    if tool_choice == "none":
        return False, None, False
    if isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
        function = tool_choice.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            raise _error("named function tool_choice requires function.name")
        return True, [function["name"]], True
    raise _error("unsupported tool_choice for qwen-agent-proxy shadow contract")


def _proxy_backend_chat(settings: QwenAgentProxySettings, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        settings.backend_base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        raise _error(f"backend chat proxy failed: {body[:500]}", status_code=502, error_type="backend_error") from exc
    except Exception as exc:  # noqa: BLE001
        raise _error(f"backend chat proxy failed: {exc!r}", status_code=502, error_type="backend_error") from exc


def _build_tool_call_response(
    *,
    public_model_id: str,
    function_name: str,
    raw_arguments: str,
    function_id: str | None,
) -> dict[str, Any]:
    tool_call_id = function_id or f"call_{uuid.uuid4().hex[:24]}"
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": public_model_id,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": raw_arguments,
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }


def _build_text_response(*, public_model_id: str, assistant_text: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": public_model_id,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": assistant_text,
                },
                "finish_reason": "stop",
            }
        ],
    }


def _model_info_payload(settings: QwenAgentProxySettings) -> dict[str, Any]:
    return {
        "data": [
            {
                "model_name": settings.public_model_id,
                "litellm_params": {
                    "model": settings.backend_model,
                    "api_base": settings.backend_base_url,
                    "max_tokens": settings.default_max_tokens,
                },
                "model_info": {
                    "key": settings.backend_model,
                    "mode": "chat",
                    "supports_system_messages": True,
                    "supports_function_calling": True,
                    "max_input_tokens": None,
                    "max_output_tokens": settings.default_max_tokens,
                    "litellm_provider": "openai",
                },
            }
        ]
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    qwen_agent, _get_chat_model = load_qwen_agent()
    settings = load_settings()
    return {
        "status": "ok",
        "qwen_agent_install_spec": QWEN_AGENT_INSTALL_SPEC,
        "qwen_agent_version": getattr(qwen_agent, "__version__", "unknown"),
        "backend_base_url": settings.backend_base_url,
        "backend_model": settings.backend_model,
        "public_model_id": settings.public_model_id,
        "use_raw_api": settings.use_raw_api,
    }


@app.get("/v1/models")
async def list_models(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    settings = load_settings()
    _require_auth(settings, authorization)
    return {
        "object": "list",
        "data": [
            {
                "id": settings.public_model_id,
                "object": "model",
                "owned_by": "qwen-agent-proxy",
            }
        ],
    }


@app.get("/v1/model/info")
@app.get("/model/info")
async def model_info(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    settings = load_settings()
    _require_auth(settings, authorization)
    return _model_info_payload(settings)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    settings = load_settings()
    _require_auth(settings, authorization)
    payload = await request.json()
    model = payload.get("model")
    if model != settings.public_model_id:
        raise _error(f"unknown model: {model!r}", status_code=404, error_type="not_found_error")
    if payload.get("stream"):
        raise _error("stream=true is unsupported for qwen-agent-proxy")

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise _error("messages must be a non-empty list")

    tools = payload.get("tools") or []
    if not tools:
        backend_payload = dict(payload)
        backend_payload["model"] = settings.backend_model
        return _proxy_backend_chat(settings, backend_payload)

    must_call, allowed_function_names, call_tools = _parse_tool_choice(payload.get("tool_choice"))
    if not call_tools:
        backend_payload = dict(payload)
        backend_payload["model"] = settings.backend_model
        backend_payload.pop("tools", None)
        backend_payload.pop("tool_choice", None)
        return _proxy_backend_chat(settings, backend_payload)

    adapter = QwenAgentAdapter(
        base_url=settings.backend_base_url,
        model=settings.backend_model,
        api_key=settings.backend_api_key,
        use_raw_api=settings.use_raw_api,
        temperature=float(payload.get("temperature", settings.default_temperature)),
        max_tokens=int(payload.get("max_tokens", settings.default_max_tokens)),
    )
    result = adapter.run_turn(
        messages=messages,
        tools=tools,
        must_call=must_call,
        allowed_function_names=allowed_function_names,
    )
    if result.status == "error":
        raise _error(result.error or "adapter failed", status_code=400)
    if result.status == "assistant_text":
        return _build_text_response(
            public_model_id=settings.public_model_id,
            assistant_text=result.assistant_text,
        )
    assert result.function_call is not None
    return _build_tool_call_response(
        public_model_id=settings.public_model_id,
        function_name=result.function_call.name,
        raw_arguments=result.function_call.raw_arguments,
        function_id=result.function_call.function_id,
    )


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
