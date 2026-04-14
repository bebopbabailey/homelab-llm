from __future__ import annotations

import json
import logging
from pathlib import Path
from sys import stderr
from typing import Any

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

logger = logging.getLogger("qwen_toolcall_posthook")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)

_TRACE_PATH = Path("/tmp/litellm_qwen_toolcall_posthook.jsonl")
_TOOL_BLOCK_START = "<tool_call>"
_TOOL_BLOCK_END = "</tool_call>"
_TARGET_MODELS = {"main"}


def _emit_trace(event: dict[str, Any]) -> None:
    payload = json.dumps(event, ensure_ascii=True, sort_keys=True)
    try:
        with _TRACE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
            handle.flush()
    except Exception:
        logger.exception("qwen_toolcall_posthook trace write failed payload=%s", payload)
    logger.info(payload)


def _normalize_model_name(model: Any) -> str:
    if not isinstance(model, str):
        return ""
    normalized = model.strip().lower()
    if "/" in normalized:
        normalized = normalized.rsplit("/", 1)[-1]
    return normalized


def _is_target_model(model: Any) -> bool:
    return _normalize_model_name(model) in _TARGET_MODELS


def _response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    return response if isinstance(response, dict) else {}


def _extract_message(body: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None, None
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        return choice, None
    return choice, message


def _extract_single_tool_name(data: dict[str, Any]) -> str | None:
    tools = data.get("tools")
    if not isinstance(tools, list) or len(tools) != 1:
        return None
    tool = tools[0]
    if not isinstance(tool, dict):
        return None
    function = tool.get("function")
    if not isinstance(function, dict):
        return None
    name = function.get("name")
    return name if isinstance(name, str) and name else None


def _extract_strict_tool_block(content: Any) -> str | None:
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    if not stripped.startswith(_TOOL_BLOCK_START) or not stripped.endswith(_TOOL_BLOCK_END):
        return None
    inner = stripped[len(_TOOL_BLOCK_START) : -len(_TOOL_BLOCK_END)].strip()
    return inner if inner else None


def _normalize_tool_payload(raw_json: str, inferred_tool_name: str | None) -> list[dict[str, Any]] | None:
    try:
        parsed = json.loads(raw_json)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None

    if "name" in parsed and "arguments" in parsed:
        name = parsed.get("name")
        arguments = parsed.get("arguments")
        if not isinstance(name, str) or not name:
            return None
        if not isinstance(arguments, dict):
            return None
    else:
        if not inferred_tool_name:
            return None
        name = inferred_tool_name
        arguments = parsed

    return [
        {
            "id": "call_qwen_tool_auto_0",
            "type": "function",
            "function": {
                "name": name,
                "arguments": json.dumps(arguments, ensure_ascii=True, separators=(",", ":")),
            },
        }
    ]


class QwenToolcallPostHook(CustomGuardrail):
    def __init__(self, guardrail_name: str, event_hook: str, default_on: bool, **kwargs):
        super().__init__(
            guardrail_name=guardrail_name,
            supported_event_hooks=[GuardrailEventHooks.post_call],
            event_hook=event_hook,
            default_on=default_on,
            **kwargs,
        )

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        event = {
            "decision": "passthrough",
            "model": _normalize_model_name(data.get("model")),
            "reason": "non_target_model",
        }
        if not _is_target_model(data.get("model")):
            _emit_trace(event)
            return response
        if data.get("stream") is True:
            event["reason"] = "streaming_request"
            _emit_trace(event)
            return response
        if data.get("tool_choice") != "auto":
            event["reason"] = "tool_choice_not_auto"
            _emit_trace(event)
            return response
        if not isinstance(data.get("tools"), list) or not data["tools"]:
            event["reason"] = "no_tools_declared"
            _emit_trace(event)
            return response

        body = _response_to_dict(response)
        choice, message = _extract_message(body)
        if choice is None or message is None:
            event["reason"] = "missing_message"
            _emit_trace(event)
            return response

        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            event["reason"] = "tool_calls_already_present"
            _emit_trace(event)
            return response

        raw_json = _extract_strict_tool_block(message.get("content"))
        if raw_json is None:
            event["reason"] = "content_not_strict_tool_block"
            _emit_trace(event)
            return response

        normalized_tool_calls = _normalize_tool_payload(
            raw_json=raw_json,
            inferred_tool_name=_extract_single_tool_name(data),
        )
        if normalized_tool_calls is None:
            event["decision"] = "non_normalizable"
            event["reason"] = "raw_tool_block_not_lossless"
            _emit_trace(event)
            return response

        message["tool_calls"] = normalized_tool_calls
        message["content"] = None
        finish_reason = choice.get("finish_reason")
        if finish_reason == "stop":
            choice["finish_reason"] = "tool_calls"
        event["decision"] = "normalized"
        event["reason"] = "strict_tool_block_rewritten"
        _emit_trace(event)
        return body
