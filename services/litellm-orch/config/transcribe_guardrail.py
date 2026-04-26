from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks


TASK_TRANSCRIBE_MODELS = {"task-transcribe", "task-transcribe-vivid"}
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

        transcript = _extract_user_text(data.get("messages") or [])
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
        user_api_key_dict: Any,
        data: dict,
        response: Any,
    ) -> Any:
        model = data.get("model")
        if model not in TASK_TRANSCRIBE_MODELS:
            return response

        message = _extract_chat_message(response)
        if not isinstance(message, dict):
            return response

        content = message.get("content")
        if not isinstance(content, str):
            return response

        cleaned = _strip_wrappers(content)
        message["content"] = cleaned
        message.pop("reasoning", None)
        message.pop("reasoning_content", None)
        message.pop("provider_specific_fields", None)

        logger.info(
            "transcribe post_call alias=%s content_len=%s cleaned_len=%s",
            model,
            len(content),
            len(cleaned),
        )
        return response
