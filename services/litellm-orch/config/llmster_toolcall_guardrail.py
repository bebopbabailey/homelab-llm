from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path
from sys import stderr
from typing import Any

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

logger = logging.getLogger("llmster_toolcall_guardrail")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)

_TRACE_PATH = Path("/tmp/litellm_llmster_toolcall_guardrail.jsonl")
_DEFAULT_TARGET_MODELS = {"deep", "fast", "code-reasoning"}
_FALLBACK_ERROR = (
    "The model returned a malformed tool call for this request. "
    "Please retry the request."
)
_FUNCTION_MARKER_RE = re.compile(r"to=functions\.([A-Za-z0-9_.-]+)")


def emit_policy_event(event: dict[str, Any]) -> None:
    payload = json.dumps(event, ensure_ascii=True, sort_keys=True)
    try:
        with _TRACE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
            handle.flush()
    except Exception:
        logger.exception("llmster_toolcall_guardrail trace write failed payload=%s", payload)
    logger.info(payload)


def _parse_model_targets(raw: Any) -> set[str]:
    if not raw:
        return set(_DEFAULT_TARGET_MODELS)
    if isinstance(raw, str):
        return {item.strip().lower() for item in raw.split(",") if item.strip()}
    if isinstance(raw, (list, tuple, set)):
        out: set[str] = set()
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.add(item.strip().lower())
        return out or set(_DEFAULT_TARGET_MODELS)
    return set(_DEFAULT_TARGET_MODELS)


def _normalize_model_name(model: Any) -> str:
    if not isinstance(model, str):
        return ""
    normalized = model.strip().lower()
    if "/" in normalized:
        normalized = normalized.rsplit("/", 1)[-1]
    return normalized


def _is_target_model(model: Any, targets: set[str]) -> bool:
    return _normalize_model_name(model) in targets


def _normalized_tool_key(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _extract_declared_tool_map(data: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    tools = data.get("tools")
    if not isinstance(tools, list):
        return out
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if isinstance(name, str) and name:
            out[_normalized_tool_key(name)] = name
    return out


def _response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    return response if isinstance(response, dict) else {}


def _extract_choice_and_message(body: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None, None
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        return choice, None
    return choice, message


def _message_strings(message: dict[str, Any]) -> list[str]:
    strings: list[str] = []
    for key in ("content", "reasoning", "reasoning_content"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            strings.append(value)
        elif isinstance(value, list):
            for part in value:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        strings.append(text)
    return strings


def _extract_balanced_json(text: str, start: int) -> str | None:
    brace_start = text.find("{", start)
    if brace_start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start : idx + 1]
    return None


def _extract_protocol_tool_call(text: str) -> tuple[str, str] | None:
    candidate = html.unescape(text)
    matches = list(_FUNCTION_MARKER_RE.finditer(candidate))
    for match in reversed(matches):
        message_idx = candidate.find("<|message|>", match.end())
        if message_idx == -1:
            continue
        raw_json = _extract_balanced_json(candidate, message_idx + len("<|message|>"))
        if raw_json is None:
            continue
        return match.group(1), raw_json
    return None


def _normalize_arguments(raw_json: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw_json)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None

    if "name" in parsed and "arguments" in parsed:
        arguments = parsed.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                return None
        if not isinstance(arguments, dict):
            return None
        return arguments

    return parsed


def _build_tool_calls(tool_name: str, raw_json: str, declared_tool_map: dict[str, str]) -> list[dict[str, Any]] | None:
    canonical_name = declared_tool_map.get(_normalized_tool_key(tool_name))
    if canonical_name is None:
        return None
    arguments = _normalize_arguments(raw_json)
    if arguments is None:
        return None
    return [
        {
            "id": "call_llmster_tool_auto_0",
            "type": "function",
            "function": {
                "name": canonical_name,
                "arguments": json.dumps(arguments, ensure_ascii=True, separators=(",", ":")),
            },
        }
    ]


def _tool_protocol_present(message: dict[str, Any]) -> bool:
    for text in _message_strings(message):
        if "to=functions." in text:
            return True
    return False


def _strip_reasoning_fields(message: dict[str, Any]) -> None:
    message.pop("reasoning", None)
    message.pop("reasoning_content", None)
    message.pop("provider_specific_fields", None)


class LlmsterToolcallGuardrail(CustomGuardrail):
    def __init__(self, guardrail_name: str, event_hook: str, default_on: bool, **kwargs):
        self.target_models = _parse_model_targets(kwargs.get("target_models"))
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
        event = {
            "decision": "passthrough",
            "reason": "non_target_model",
            "model": _normalize_model_name(data.get("model")),
            "stream_before": data.get("stream"),
        }
        if not _is_target_model(data.get("model"), self.target_models):
            emit_policy_event(event)
            return data
        if data.get("tool_choice") != "auto":
            event["reason"] = "tool_choice_not_auto"
            emit_policy_event(event)
            return data
        if not isinstance(data.get("tools"), list) or not data["tools"]:
            event["reason"] = "no_tools_declared"
            emit_policy_event(event)
            return data
        if data.get("stream") is not True:
            event["reason"] = "already_nonstream"
            emit_policy_event(event)
            return data

        data["stream"] = False
        event["decision"] = "normalized"
        event["reason"] = "forced_nonstream_for_tool_contract"
        event["stream_after"] = data.get("stream")
        emit_policy_event(event)
        return data

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        event = {
            "decision": "passthrough",
            "reason": "non_target_model",
            "model": _normalize_model_name(data.get("model")),
        }
        if not _is_target_model(data.get("model"), self.target_models):
            emit_policy_event(event)
            return response
        if data.get("tool_choice") != "auto":
            event["reason"] = "tool_choice_not_auto"
            emit_policy_event(event)
            return response
        declared_tool_map = _extract_declared_tool_map(data)
        if not declared_tool_map:
            event["reason"] = "no_tools_declared"
            emit_policy_event(event)
            return response

        body = _response_to_dict(response)
        choice, message = _extract_choice_and_message(body)
        if choice is None or message is None:
            event["reason"] = "missing_message"
            emit_policy_event(event)
            return response

        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            event["reason"] = "tool_calls_already_present"
            emit_policy_event(event)
            return response

        protocol_present = _tool_protocol_present(message)
        extracted: tuple[str, str] | None = None
        for text in _message_strings(message):
            extracted = _extract_protocol_tool_call(text)
            if extracted is not None:
                break

        if extracted is None:
            event["reason"] = "no_protocol_tool_call_found" if not protocol_present else "protocol_marker_without_message_payload"
            emit_policy_event(event)
            if not protocol_present:
                return response
            message["content"] = _FALLBACK_ERROR
            message["tool_calls"] = []
            _strip_reasoning_fields(message)
            choice["finish_reason"] = "stop"
            event["decision"] = "fallback_error"
            emit_policy_event(event)
            return body

        tool_name, raw_json = extracted
        normalized_tool_calls = _build_tool_calls(tool_name, raw_json, declared_tool_map)
        if normalized_tool_calls is None:
            message["content"] = _FALLBACK_ERROR
            message["tool_calls"] = []
            _strip_reasoning_fields(message)
            choice["finish_reason"] = "stop"
            event["decision"] = "fallback_error"
            event["reason"] = "tool_call_not_lossless"
            event["tool_name"] = tool_name
            emit_policy_event(event)
            return body

        message["content"] = None
        message["tool_calls"] = normalized_tool_calls
        _strip_reasoning_fields(message)
        if choice.get("finish_reason") == "stop":
            choice["finish_reason"] = "tool_calls"
        event["decision"] = "normalized"
        event["reason"] = "protocol_tool_call_rewritten"
        event["tool_name"] = normalized_tool_calls[0]["function"]["name"]
        emit_policy_event(event)
        return body
