from __future__ import annotations

import re
from typing import Any, AsyncGenerator, Optional

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

_HARMONY_HEADER_RE = re.compile(r"<\|channel\|>\s*([a-zA-Z0-9_-]+)\s*<\|message\|>", re.DOTALL)
_HARMONY_REQUIRED_CHANNELS = {"analysis", "final"}
_DEFAULT_TARGET_MODELS = {"deep", "fast", "boost", "boost-deep"}

# Keep task-transcribe behavior fully controlled by transcribe guardrail.
_EXCLUDED_MODELS = {"task-transcribe", "task-transcribe-vivid"}


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


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


def _is_strict_harmony_payload(text: str) -> bool:
    if "<|channel|>" not in text or "<|message|>" not in text:
        return False

    matches = list(_HARMONY_HEADER_RE.finditer(text))
    if not matches:
        return False

    channels = {m.group(1).strip().lower() for m in matches}
    return bool(channels & _HARMONY_REQUIRED_CHANNELS)


def _strip_protocol_tokens(text: str) -> str:
    return re.sub(r"<\|[^>]+?\|>", " ", text)


def _extract_harmony_final_text(text: str) -> Optional[str]:
    if not _is_strict_harmony_payload(text):
        return None

    matches = list(_HARMONY_HEADER_RE.finditer(text))
    channel_messages: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        channel = match.group(1).strip().lower()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        message = re.sub(r"\s+", " ", _strip_protocol_tokens(text[start:end])).strip()
        if message:
            channel_messages.append((channel, message))

    finals = [msg for ch, msg in channel_messages if ch == "final" and msg]
    if finals:
        return finals[-1]
    return None


def normalize_assistant_text(text: str) -> tuple[str, bool]:
    original = text.strip()
    if not original:
        return text, False

    harmony_final = _extract_harmony_final_text(original)
    if harmony_final:
        return harmony_final, harmony_final != original

    return text, False


def _extract_model_name(data: dict) -> str:
    model = data.get("model", "")
    return model if isinstance(model, str) else ""


def _is_target_model(model: str, targets: set[str]) -> bool:
    normalized = model.strip().lower()
    if normalized in targets:
        return True
    # Requests may contain provider-prefixed model names.
    if "/" in normalized:
        normalized = normalized.rsplit("/", 1)[-1]
        if normalized in targets:
            return True
    # Handle direct backend ids if an alias is bypassed.
    return "gpt-oss" in normalized


def _message_content_getter(response: Any) -> Optional[str]:
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
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks) if chunks else None
    return None


def _message_content_setter(response: Any, content: str) -> Any:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                message["content"] = content
                message.pop("reasoning_content", None)
                message.pop("reasoning", None)
                message.pop("provider_specific_fields", None)
    return response


class HarmonyGuardrail(CustomGuardrail):
    """Normalize GPT-OSS Harmony and Qwen think-tag output for downstream clients."""

    def __init__(self, guardrail_name: str, event_hook: str, default_on: bool, **kwargs):
        self.target_models = _parse_model_targets(kwargs.get("target_models"))
        self.coerce_stream_false = _parse_bool(kwargs.get("coerce_stream_false"), default=False)
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
        model = _extract_model_name(data)
        if model in _EXCLUDED_MODELS:
            return data
        if not _is_target_model(model, self.target_models):
            return data

        if self.coerce_stream_false and data.get("stream") is True:
            data["stream"] = False

        messages = data.get("messages")
        if not isinstance(messages, list):
            return data

        changed = False
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                normalized, did_change = normalize_assistant_text(content)
                if did_change:
                    msg["content"] = normalized
                    msg.pop("reasoning", None)
                    msg.pop("reasoning_content", None)
                    msg.pop("provider_specific_fields", None)
                    changed = True

        if changed:
            data["messages"] = messages
        return data

    async def async_post_call_success_hook(self, data: dict, user_api_key_dict: Any, response: Any) -> Any:
        model = _extract_model_name(data)
        if model in _EXCLUDED_MODELS:
            return response
        if not _is_target_model(model, self.target_models):
            return response

        content = _message_content_getter(response)
        if not content:
            return response

        normalized, changed = normalize_assistant_text(content)
        if changed:
            return _message_content_setter(response, normalized)

        return response

    async def async_post_call_streaming_iterator_hook(
        self,
        user_api_key_dict: Any,
        response: Any,
        request_data: dict,
    ) -> AsyncGenerator[Any, None]:
        async for item in response:
            yield item
