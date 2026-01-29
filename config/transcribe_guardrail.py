from __future__ import annotations

import re
from typing import Any, Optional

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

TRANSCRIBE_PERSONAS = {
    "p-transcribe",
    "p-transcribe-vivid",
    "p-transcribe-clarify",
    "p-transcribe-md",
    "task-transcribe",
    "task-transcribe-vivid",
}


def _extract_text(response: Any) -> Optional[str]:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    if not isinstance(response, dict):
        return None
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
    return None


def _strip_wrappers(text: str) -> str:
    if not isinstance(text, str):
        return text
    original = text
    text = text.strip()

    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`\n ")
    text = text.strip("\"'`\n ")

    patterns = [
        r"^#+\s*cleaned transcript\s*(?:[:\-])\s*",
        r"^\*\*cleaned transcript\*\*\s*(?:[:\-])\s*",
        r"^cleaned transcript\s*(?:[:\-])\s*",
        r"^here is the cleaned transcript\s*(?:[:\-])\s*",
        r"^here's the cleaned transcript\s*(?:[:\-])\s*",
        r"^cleaned transcript output\s*(?:[:\-])\s*",
    ]
    lowered = text.lower()
    for pat in patterns:
        match = re.match(pat, lowered, flags=re.IGNORECASE)
        if match:
            text = text[match.end():].lstrip()
            break

    return text if text else original


class TranscribeGuardrail(CustomGuardrail):
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
        user_api_key_dict: Any,
        data: dict,
        response: Any,
    ) -> Any:
        metadata = data.get("metadata") or data.get("litellm_metadata") or {}
        persona = metadata.get("persona")
        if persona not in TRANSCRIBE_PERSONAS:
            return response

        if data.get("stream"):
            return response

        output = _extract_text(response)
        if not output:
            return response

        cleaned = _strip_wrappers(output)
        if cleaned == output:
            return response

        if hasattr(response, "model_dump"):
            try:
                response = response.model_dump()
            except Exception:
                pass
        if isinstance(response, dict):
            choices = response.get("choices")
            if isinstance(choices, list) and choices:
                if isinstance(choices[0], dict):
                    message = choices[0].get("message")
                    if isinstance(message, dict):
                        message["content"] = cleaned
                        return response
        return response
