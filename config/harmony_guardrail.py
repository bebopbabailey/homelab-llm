from __future__ import annotations

import copy
import re
from typing import Any, AsyncGenerator, Optional

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

_HARMONY_HEADER_RE = re.compile(r"<\|channel\|>\s*([a-zA-Z0-9_-]+)\s*<\|message\|>", re.DOTALL)
_HARMONY_TOKEN_RE = re.compile(r"<\|[^>]+?\|>")
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_LEAK_PREFIX_RE = re.compile(
    r"^\s*(the user says|user says|we need to|i need to|probably wants|the user might)\b",
    re.IGNORECASE,
)

# Keep task-transcribe behavior fully controlled by transcribe guardrail.
_EXCLUDED_MODELS = {"task-transcribe", "task-transcribe-vivid"}


def _strip_protocol_tokens(text: str) -> str:
    text = _HARMONY_TOKEN_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_harmony_final_text(text: str) -> Optional[str]:
    if "<|channel|>" not in text or "<|message|>" not in text:
        return None

    matches = list(_HARMONY_HEADER_RE.finditer(text))
    if not matches:
        return None

    channel_messages: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        channel = match.group(1).strip().lower()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        message = _strip_protocol_tokens(text[start:end])
        if message:
            channel_messages.append((channel, message))

    finals = [msg for ch, msg in channel_messages if ch == "final" and msg]
    if finals:
        return finals[-1]

    # Fallback when a response streams/stops before an explicit `final` channel.
    preferred_channels = {"assistant", "response", "output"}
    preferred = [msg for ch, msg in channel_messages if ch in preferred_channels and msg]
    if preferred:
        return preferred[-1]

    non_analysis = [msg for ch, msg in channel_messages if ch != "analysis" and msg]
    if non_analysis:
        return non_analysis[-1]

    if channel_messages:
        return channel_messages[-1][1]
    return None


def _strip_think_blocks(text: str) -> str:
    stripped = _THINK_BLOCK_RE.sub("", text)
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()
    return stripped if stripped else text.strip()


def _last_user_text(data: dict) -> Optional[str]:
    messages = data.get("messages")
    if not isinstance(messages, list):
        return None
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return None


def _looks_like_analysis_leak(text: str) -> bool:
    if not text:
        return False
    if _LEAK_PREFIX_RE.search(text):
        return True
    # Common degenerate loop observed in leakage.
    if text.count("The user?") >= 3:
        return True
    return False


def _safe_fallback_reply(last_user: Optional[str]) -> str:
    if not last_user:
        return "Could you clarify what you want me to do?"
    short = last_user.strip().replace("\n", " ")
    if len(short) > 120:
        short = short[:117] + "..."
    return f'Could you clarify what you mean by "{short}"?'


def normalize_assistant_text(text: str) -> tuple[str, bool]:
    original = text.strip()
    if not original:
        return text, False

    harmony_final = _extract_harmony_final_text(original)
    if harmony_final:
        return harmony_final, harmony_final != original

    if "<|" in original and "|>" in original:
        stripped = _strip_protocol_tokens(original)
        return stripped, stripped != original

    if "<think>" in original.lower() and "</think>" in original.lower():
        cleaned = _strip_think_blocks(original)
        return cleaned, cleaned != original

    return text, False


def _extract_model_name(data: dict) -> str:
    model = data.get("model", "")
    return model if isinstance(model, str) else ""


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


def _extract_stream_content(item: Any) -> str:
    if isinstance(item, dict):
        try:
            choices = item.get("choices") or []
            content_parts: list[str] = []
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta") or {}
                if not isinstance(delta, dict):
                    continue
                content = delta.get("content")
                if isinstance(content, str):
                    content_parts.append(content)
            return "".join(content_parts)
        except Exception:
            return ""

    try:
        choices = getattr(item, "choices", None)
        if not choices:
            return ""
        content_parts: list[str] = []
        for choice in choices:
            delta = getattr(choice, "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if isinstance(content, str):
                content_parts.append(content)
        return "".join(content_parts)
    except Exception:
        return ""


def _set_stream_content(item: Any, text: str) -> Any:
    if isinstance(item, dict):
        try:
            choices = item.get("choices")
            if not choices or not isinstance(choices, list):
                return item
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                return item
            delta = first_choice.get("delta")
            if not isinstance(delta, dict):
                return item
            delta["content"] = text
            return item
        except Exception:
            return item

    try:
        choices = getattr(item, "choices", None)
        if not choices:
            return item
        first_choice = choices[0]
        delta = getattr(first_choice, "delta", None)
        if delta is not None:
            setattr(delta, "content", text)
    except Exception:
        pass
    return item


class HarmonyGuardrail(CustomGuardrail):
    """Normalize GPT-OSS Harmony and Qwen think-tag output for downstream clients."""

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
        model = _extract_model_name(data)
        if model in _EXCLUDED_MODELS:
            return data

        messages = data.get("messages")
        if not isinstance(messages, list):
            return data

        changed = False
        for msg in messages:
            if not isinstance(msg, dict):
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

        content = _message_content_getter(response)
        if not content:
            return response

        normalized, changed = normalize_assistant_text(content)
        if changed:
            return _message_content_setter(response, normalized)

        if _looks_like_analysis_leak(content):
            return _message_content_setter(response, _safe_fallback_reply(_last_user_text(data)))

        return response

    async def async_post_call_streaming_iterator_hook(
        self,
        user_api_key_dict: Any,
        response: Any,
        request_data: dict,
    ) -> AsyncGenerator[Any, None]:
        model = _extract_model_name(request_data)
        if model in _EXCLUDED_MODELS:
            async for item in response:
                yield item
            return

        buffered_text: list[str] = []
        first_content_chunk: Any = None
        non_content_chunks: list[Any] = []
        finish_chunks: list[Any] = []

        async for item in response:
            chunk_text = _extract_stream_content(item)
            if chunk_text:
                buffered_text.append(chunk_text)
                if first_content_chunk is None:
                    first_content_chunk = copy.deepcopy(item)
                continue

            try:
                choices = getattr(item, "choices", None)
                finish_reason = getattr(choices[0], "finish_reason", None) if choices else None
            except Exception:
                finish_reason = None

            if finish_reason:
                finish_chunks.append(item)
            else:
                non_content_chunks.append(item)

        for item in non_content_chunks:
            yield item

        joined = "".join(buffered_text).strip()
        if first_content_chunk is not None and joined:
            normalized, _ = normalize_assistant_text(joined)
            if _looks_like_analysis_leak(normalized):
                normalized = _safe_fallback_reply(_last_user_text(request_data))
            yield _set_stream_content(first_content_chunk, normalized)

        for item in finish_chunks:
            yield item
