from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

import httpx
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.integrations.dotprompt.dotprompt_manager import DotpromptManager
from litellm.integrations.dotprompt.prompt_manager import PromptManager
from litellm.types.guardrails import GuardrailEventHooks


TASK_JSON_ALIAS = "task-json"
PROVIDER_MODEL = "openai/llmster-gpt-oss-20b-mxfp4-gguf"
PROMPT_ID = "task-json"
logger = logging.getLogger("task_json_guardrail")
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_PROMPT_MANAGER = PromptManager(prompt_directory=str(_PROMPT_DIR))
_DOTPROMPT = DotpromptManager(prompt_directory=str(_PROMPT_DIR))
_ATTRIBUTE_KEYS = {"emotion", "urgency", "person", "place", "date", "time"}


def _canonical_payload(attributes: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return {
        "todo": [],
        "grocery": [],
        "purchase": [],
        "other": {
            "items": [],
            "attributes": attributes or {},
        },
    }


TASK_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "task_json_payload",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "todo": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "grocery": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "purchase": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "other": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "attributes": {
                            "type": "object",
                            "additionalProperties": {
                                "type": ["string", "number", "boolean", "null"]
                            },
                        },
                    },
                    "required": ["items", "attributes"],
                    "additionalProperties": False,
                },
            },
            "required": ["todo", "grocery", "purchase", "other"],
            "additionalProperties": False,
        },
    },
}


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _clean_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _dedupe_strings(values: list[str], seen: Optional[set[str]] = None) -> list[str]:
    deduped: list[str] = []
    seen_keys = seen if seen is not None else set()
    for value in values:
        cleaned = _clean_string(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(cleaned)
    return deduped


def _extract_user_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return "\n\n".join(parts).strip()


def _extract_transcript(messages: Any) -> str:
    transcript = _extract_user_text(messages)
    if not transcript:
        return ""
    if "Transcript:" in transcript:
        return transcript.split("Transcript:", 1)[1].strip()
    return transcript


def _render_prompt_messages(prompt_variables: dict[str, str]) -> list[dict[str, Any]]:
    rendered = _PROMPT_MANAGER.render(
        prompt_id=PROMPT_ID,
        prompt_variables=prompt_variables,
    )
    return _DOTPROMPT._convert_to_messages(rendered)


def _extract_json_object_text(text: str) -> Optional[str]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
        stripped = stripped.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        return match.group(0)
    return None


def _collect_string_items(value: Any) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        cleaned = _clean_string(value)
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        for item in value:
            items.extend(_collect_string_items(item))
        return items
    if isinstance(value, dict):
        for key in ("text", "item", "name", "title", "value"):
            cleaned = _clean_string(value.get(key))
            if cleaned:
                return [cleaned]
        return []
    return []


def _merge_attribute_scalar(target: dict[str, Any], key: str, value: Any) -> None:
    if not _is_scalar(value):
        return
    if not isinstance(key, str) or not key:
        return
    target.setdefault(key, value)


def _salvage_unknown(key: str, value: Any, payload: dict[str, Any]) -> None:
    items = payload["other"]["items"]
    attributes = payload["other"]["attributes"]
    if key in _ATTRIBUTE_KEYS and _is_scalar(value):
        _merge_attribute_scalar(attributes, key, value)
        return
    if isinstance(value, dict):
        for subkey, subvalue in value.items():
            if isinstance(subkey, str) and subkey in _ATTRIBUTE_KEYS and _is_scalar(subvalue):
                _merge_attribute_scalar(attributes, subkey, subvalue)
            else:
                items.extend(_collect_string_items(subvalue))
        return
    if _is_scalar(value):
        _merge_attribute_scalar(attributes, key, value)
        return
    items.extend(_collect_string_items(value))


def _normalize_payload(raw: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw, dict):
        return None

    payload = _canonical_payload()
    payload["todo"] = _collect_string_items(raw.get("todo"))
    payload["grocery"] = _collect_string_items(raw.get("grocery"))
    payload["purchase"] = _collect_string_items(raw.get("purchase"))

    other = raw.get("other")
    if isinstance(other, dict):
        payload["other"]["items"] = _collect_string_items(other.get("items"))
        attributes = other.get("attributes")
        if isinstance(attributes, dict):
            for key, value in attributes.items():
                if isinstance(key, str) and _is_scalar(value):
                    payload["other"]["attributes"][key] = value
        for key, value in other.items():
            if key in {"items", "attributes"}:
                continue
            _salvage_unknown(key, value, payload)
    elif other is not None:
        payload["other"]["items"] = _collect_string_items(other)

    for key, value in raw.items():
        if key in {"todo", "grocery", "purchase", "other"}:
            continue
        _salvage_unknown(key, value, payload)

    seen: set[str] = set()
    payload["todo"] = _dedupe_strings(payload["todo"], seen)
    payload["grocery"] = _dedupe_strings(payload["grocery"], seen)
    payload["purchase"] = _dedupe_strings(payload["purchase"], seen)
    payload["other"]["items"] = _dedupe_strings(payload["other"]["items"], seen)
    return payload


def _extract_chat_content(response: Any) -> Optional[str]:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    if not isinstance(response, dict):
        return None
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if isinstance(content, str) else None


def _set_chat_content(response: Any, content: str) -> Any:
    if hasattr(response, "model_dump"):
        response = response.model_dump()
    if not isinstance(response, dict):
        return response
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return response
    first = choices[0]
    if not isinstance(first, dict):
        return response
    message = first.get("message")
    if not isinstance(message, dict):
        return response
    message["content"] = content
    for field in ("reasoning", "reasoning_content"):
        message.pop(field, None)
    first.pop("reasoning", None)
    return response


def _is_task_json_request(data: dict[str, Any]) -> bool:
    if data.get("model") == TASK_JSON_ALIAS:
        return True
    response_format = data.get("response_format")
    if not isinstance(response_format, dict):
        return False
    schema = response_format.get("json_schema")
    return isinstance(schema, dict) and schema.get("name") == "task_json_payload"


async def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
    return None


async def _repair_once(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    api_base = data.get("api_base")
    if not isinstance(api_base, str) or not api_base:
        return None
    transcript = _extract_transcript(data.get("messages"))
    if not transcript:
        return None
    headers = {"Content-Type": "application/json"}
    api_key = data.get("api_key")
    if isinstance(api_key, str) and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": PROVIDER_MODEL,
        "messages": _render_prompt_messages({"user_message": transcript}),
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 1024,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "stream": False,
        "response_format": TASK_JSON_SCHEMA,
    }
    return await _post_json(f"{api_base}/chat/completions", headers, payload)


def _parse_and_normalize_content(content: str) -> Optional[dict[str, Any]]:
    object_text = _extract_json_object_text(content)
    if not object_text:
        return None
    try:
        raw = json.loads(object_text)
    except json.JSONDecodeError:
        return None
    return _normalize_payload(raw)


class TaskJsonGuardrail(CustomGuardrail):
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
        if data.get("model") != TASK_JSON_ALIAS:
            return data

        transcript = _extract_user_text(data.get("messages"))
        data["model"] = PROVIDER_MODEL
        data["messages"] = _render_prompt_messages({"user_message": transcript})
        data.pop("prompt_variables", None)
        data.pop("tools", None)
        data.pop("tool_choice", None)
        data.pop("parallel_tool_calls", None)
        data.pop("functions", None)
        data.pop("function_call", None)
        data["temperature"] = 0.0
        data["top_p"] = 1.0
        data["max_tokens"] = 1024
        data["presence_penalty"] = 0.0
        data["frequency_penalty"] = 0.0
        data["stream"] = False
        data["response_format"] = TASK_JSON_SCHEMA
        logger.info("task-json pre_call transcript_len=%s", len(transcript))
        return data

    async def async_post_call_success_hook(
        self,
        user_api_key_dict: Any,
        data: dict,
        response: Any,
    ) -> Any:
        if not _is_task_json_request(data):
            return response

        content = _extract_chat_content(response)
        normalized = _parse_and_normalize_content(content) if isinstance(content, str) else None
        if normalized is None:
            try:
                repair_response = await _repair_once(data)
            except Exception:
                logger.exception("task-json repair failed")
                repair_response = None
            if repair_response is not None:
                repaired_content = _extract_chat_content(repair_response)
                if isinstance(repaired_content, str):
                    normalized = _parse_and_normalize_content(repaired_content)

        if normalized is None:
            normalized = _canonical_payload({"guardrail_status": "repair_failed"})

        minified = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
        logger.info(
            "task-json post_call todo=%s grocery=%s purchase=%s other_items=%s",
            len(normalized["todo"]),
            len(normalized["grocery"]),
            len(normalized["purchase"]),
            len(normalized["other"]["items"]),
        )
        return _set_chat_content(response, minified)
