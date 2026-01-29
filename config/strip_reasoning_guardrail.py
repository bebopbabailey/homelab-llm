from __future__ import annotations

from typing import Any

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

TRANSCRIPT_PERSONAS = {
    "char-transcribe",
    "p-transcribe",
    "p-transcribe-vivid",
    "p-transcribe-clarify",
    "p-transcribe-md",
    "task-transcribe",
    "task-transcribe-vivid",
}


def _strip_reasoning_fields(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    payload = {**payload}
    payload.pop("reasoning_content", None)
    if isinstance(payload.get("provider_specific_fields"), dict):
        psf = {**payload["provider_specific_fields"]}
        psf.pop("reasoning_content", None)
        payload["provider_specific_fields"] = psf
    if isinstance(payload.get("message"), dict):
        msg = {**payload["message"]}
        msg.pop("reasoning_content", None)
        if isinstance(msg.get("provider_specific_fields"), dict):
            mpf = {**msg["provider_specific_fields"]}
            mpf.pop("reasoning_content", None)
            msg["provider_specific_fields"] = mpf
        payload["message"] = msg
    return payload


class StripReasoningGuardrail(CustomGuardrail):
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
        if hasattr(response, "model_dump"):
            try:
                response = response.model_dump()
            except Exception:
                pass
        metadata = data.get("metadata") or data.get("litellm_metadata") or {}
        persona = metadata.get("persona") or data.get("model")
        if persona not in TRANSCRIPT_PERSONAS:
            return response

        if isinstance(response, dict):
            response = {**response}
            if isinstance(response.get("choices"), list):
                response["choices"] = [
                    _strip_reasoning_fields(choice) for choice in response["choices"]
                ]
            response = _strip_reasoning_fields(response)
        return response
