from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks


TASK_TRANSCRIBE_MODELS = {"task-transcribe", "task-transcribe-vivid"}
RESPONSES_MIN_OUTPUT_TOKENS = {
    "task-transcribe": 384,
    "task-transcribe-vivid": 256,
}
logger = logging.getLogger("transcribe_guardrail")

try:
    from config.transcribe_utils import strip_punct_outside_words, strip_wrappers
except ModuleNotFoundError:
    _UTILS_PATH = Path(__file__).with_name("transcribe_utils.py")
    _UTILS_SPEC = importlib.util.spec_from_file_location("transcribe_utils", _UTILS_PATH)
    if _UTILS_SPEC is None or _UTILS_SPEC.loader is None:
        raise ImportError(f"Unable to load transcribe_utils from {_UTILS_PATH}")
    _UTILS_MODULE = importlib.util.module_from_spec(_UTILS_SPEC)
    _UTILS_SPEC.loader.exec_module(_UTILS_MODULE)
    strip_punct_outside_words = _UTILS_MODULE.strip_punct_outside_words
    strip_wrappers = _UTILS_MODULE.strip_wrappers


PROMPT_ID_BY_MODEL = {
    "task-transcribe": "task-transcribe",
    "task-transcribe-vivid": "task-transcribe-vivid",
}

def _extract_user_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return "\n\n".join(parts).strip()


def _flatten_responses_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_responses_text(item) for item in value)
    if isinstance(value, dict):
        if value.get("type") in {"input_text", "output_text", "text"}:
            return _flatten_responses_text(value.get("text") or value.get("value"))
        if "content" in value:
            return _flatten_responses_text(value.get("content"))
        if "input" in value:
            return _flatten_responses_text(value.get("input"))
        return _flatten_responses_text(value.get("text"))
    return str(value)


def _extract_responses_input_text(input_value: Any) -> str:
    if isinstance(input_value, str):
        return input_value.strip()
    if not isinstance(input_value, list):
        return ""
    parts: list[str] = []
    for item in input_value:
        if not isinstance(item, dict):
            continue
        if item.get("role") != "user":
            continue
        text = _flatten_responses_text(item.get("content"))
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts).strip()


def _extract_chat_message(response: Any) -> dict[str, Any] | None:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass

    if not isinstance(response, dict):
        return None

    choices = response.get("choices")
    if not (isinstance(choices, list) and choices):
        return None

    first = choices[0]
    if not isinstance(first, dict):
        return None

    message = first.get("message")
    return message if isinstance(message, dict) else None


def _response_to_dict(response: Any) -> dict[str, Any] | None:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    return response if isinstance(response, dict) else None


def _extract_responses_output_text(response: Any) -> str | None:
    body = _response_to_dict(response)
    if not body:
        return None
    direct = _flatten_responses_text(body.get("output_text"))
    if direct.strip():
        return direct.strip()
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        text = _flatten_responses_text(item.get("content"))
        if text.strip():
            return text.strip()
    return None


def _set_chat_content(response: Any, content: str) -> Any:
    if hasattr(response, "model_dump"):
        response = response.model_dump()
    if not isinstance(response, dict):
        return response
    choices = response.get("choices")
    if not (isinstance(choices, list) and choices and isinstance(choices[0], dict)):
        return response
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return response
    message["content"] = content
    message.pop("reasoning", None)
    message.pop("reasoning_content", None)
    message.pop("provider_specific_fields", None)
    return response


def _set_responses_output_text(response: Any, content: str) -> Any:
    body = _response_to_dict(response)
    if not body:
        return response
    body["output"] = [
        {
            "id": body.get("id", "resp_task_alias"),
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": content, "annotations": []}],
        }
    ]
    body["output_text"] = content
    body.pop("reasoning", None)
    return body

_strip_wrappers = strip_wrappers
_preprocess_transcript = strip_punct_outside_words


class TranscribeGuardrail(CustomGuardrail):
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
        model = data.get("model")
        if model not in TASK_TRANSCRIBE_MODELS:
            return data

        if call_type in {"responses", "aresponses"}:
            transcript = _extract_responses_input_text(data.get("input"))
            current_budget = data.get("max_output_tokens")
            minimum = RESPONSES_MIN_OUTPUT_TOKENS[model]
            if not isinstance(current_budget, int) or current_budget < minimum:
                data["max_output_tokens"] = minimum
        else:
            transcript = _extract_user_text(data.get("messages") or [])
            current_budget = data.get("max_tokens")
            minimum = RESPONSES_MIN_OUTPUT_TOKENS[model]
            if not isinstance(current_budget, int) or current_budget < minimum:
                data["max_tokens"] = minimum
        transcript = _preprocess_transcript(transcript) if transcript else ""

        prompt_variables = dict(data.get("prompt_variables") or {})
        prompt_variables["user_message"] = transcript
        if model == "task-transcribe-vivid":
            prompt_variables.setdefault("audience", "")
            prompt_variables.setdefault("tone", "")

        data["prompt_id"] = PROMPT_ID_BY_MODEL[model]
        data["prompt_variables"] = prompt_variables
        data["stream"] = False

        logger.info(
            "transcribe pre_call alias=%s prompt_id=%s transcript_len=%s prompt_vars=%s",
            model,
            data["prompt_id"],
            len(transcript),
            sorted(prompt_variables.keys()),
        )
        return data

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        model = data.get("model")
        if model not in TASK_TRANSCRIBE_MODELS:
            return response

        body = _response_to_dict(response)
        if body and body.get("object") == "response":
            content = _extract_responses_output_text(body)
            if not isinstance(content, str):
                return response
            cleaned = _strip_wrappers(content)
            logger.info(
                "transcribe post_call alias=%s content_len=%s cleaned_len=%s",
                model,
                len(content),
                len(cleaned),
            )
            return _set_responses_output_text(body, cleaned)

        message = _extract_chat_message(response)
        if not isinstance(message, dict):
            return response

        content = message.get("content")
        if not isinstance(content, str):
            return response

        cleaned = _strip_wrappers(content)

        logger.info(
            "transcribe post_call alias=%s content_len=%s cleaned_len=%s",
            model,
            len(content),
            len(cleaned),
        )
        return _set_chat_content(response, cleaned)
