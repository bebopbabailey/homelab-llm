from __future__ import annotations

from typing import Any

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

_DEFAULT_TARGET_MODELS = {"deep", "fast", "code-reasoning"}


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


class GPTRequestDefaults(CustomGuardrail):
    """Inject only the current GPT request defaults that cannot be set upstream."""

    def __init__(self, guardrail_name: str, event_hook: str, default_on: bool, **kwargs):
        self.target_models = _parse_model_targets(kwargs.get("target_models"))
        super().__init__(
            guardrail_name=guardrail_name,
            supported_event_hooks=[GuardrailEventHooks.pre_call],
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
        if _normalize_model_name(data.get("model")) not in self.target_models:
            return data
        if call_type in {"responses", "aresponses"}:
            reasoning = data.get("reasoning")
            if not isinstance(reasoning, dict):
                reasoning = {}
            if not reasoning.get("effort"):
                reasoning["effort"] = "low"
            data["reasoning"] = reasoning
        elif not data.get("reasoning_effort"):
            data["reasoning_effort"] = "low"
        return data
