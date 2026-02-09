from __future__ import annotations

import json
from typing import Any, Optional, Dict, List

import litellm
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks


TARGET_PROMPT_IDS = {"json-clerk"}  # add more prompt_ids if you want


def _extract_assistant_text(response: Any) -> Optional[str]:
    # Supports both pydantic-ish and dict responses
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    if not isinstance(response, dict):
        return None
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict):
            content = msg.get("content")
            return content if isinstance(content, str) else None
    return None


def _set_assistant_text(response: Any, new_text: str) -> Any:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            msg = choices[0].get("message")
            if isinstance(msg, dict):
                msg["content"] = new_text
                # strip provider extras if present
                msg.pop("reasoning_content", None)
                msg.pop("provider_specific_fields", None)
    return response


def _validate_schema(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != {"categories"}:
        return False
    cats = obj.get("categories")
    if not isinstance(cats, list):
        return False
    for c in cats:
        if not isinstance(c, dict):
            return False
        if set(c.keys()) != {"name", "items"}:
            return False
        if not isinstance(c["name"], str):
            return False
        if not isinstance(c["items"], list):
            return False
        for it in c["items"]:
            if not isinstance(it, dict):
                return False
            if set(it.keys()) != {"text", "kind", "confidence", "notes"}:
                return False
            if not isinstance(it["text"], str):
                return False
            if it["kind"] not in {"todo", "buy", "errand", "call", "idea", "other"}:
                return False
            if not isinstance(it["confidence"], (int, float)):
                return False
            if not isinstance(it["notes"], str):
                return False
    return True


class JsonClerkGuardrail(CustomGuardrail):
    """
    Post-call: ensure the model returns JSON matching our schema.
    If invalid, do ONE repair call (non-streaming) and replace response content.
    """

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
        # Only apply when prompt_id is json-clerk (or add routing logic)
        prompt_id = data.get("prompt_id")
        if prompt_id not in TARGET_PROMPT_IDS:
            return response

        # Don't loop repairs
        metadata = data.get("metadata") or {}
        if metadata.get("json_clerk_repair_attempted") is True:
            return response

        # Skip streaming (you can implement streaming iterator hook later)
        if data.get("stream"):
            return response

        text = _extract_assistant_text(response)
        if not text:
            return response

        # First parse attempt
        try:
            obj = json.loads(text)
            if _validate_schema(obj):
                # normalize: ensure compact JSON
                return _set_assistant_text(response, json.dumps(obj, ensure_ascii=False))
        except Exception:
            pass

        # Repair call: ask model to output ONLY valid JSON matching schema
        # Use the original user message content as the source of truth.
        messages = data.get("messages") or []
        user_text = ""
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "user" and isinstance(m.get("content"), str):
                user_text = m["content"]
                break

        repair_messages = [
            {
                "role": "system",
                "content": (
                    "You must output ONLY valid JSON matching this exact schema:\n"
                    '{ "categories": [ { "name": string, "items": [ { "text": string, '
                    '"kind": "todo"|"buy"|"errand"|"call"|"idea"|"other", "confidence": number, "notes": string } ] } ] }\n'
                    "No extra keys. No markdown. No commentary."
                ),
            },
            {"role": "user", "content": f"Source text:\n{user_text}\n\nYour previous (invalid) output:\n{text}"},
        ]

        # IMPORTANT: mark attempt to avoid infinite recursion
        data["metadata"] = dict(metadata, json_clerk_repair_attempted=True)

        # Call the SAME model alias (so routing stays consistent).
        # If you prefer calling the resolved provider model, you can pass that instead.
        repair = await litellm.acompletion(
            model=data["model"],  # model alias (e.g., "task-transcribe" style) - adjust if needed
            messages=repair_messages,
            temperature=0.0,
            top_p=1.0,
            max_tokens=1200,
        )

        repaired_text = _extract_assistant_text(repair)
        if not repaired_text:
            return response

        # Final parse; if still invalid, return original response (or raise)
        try:
            obj2 = json.loads(repaired_text)
            if _validate_schema(obj2):
                return _set_assistant_text(response, json.dumps(obj2, ensure_ascii=False))
        except Exception:
            pass

        return response