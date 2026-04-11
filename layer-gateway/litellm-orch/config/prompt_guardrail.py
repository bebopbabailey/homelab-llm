from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.integrations.dotprompt.dotprompt_manager import DotpromptManager
from litellm.integrations.dotprompt.prompt_manager import PromptManager
from litellm.types.guardrails import GuardrailEventHooks

logger = logging.getLogger("prompt_guardrail")

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_PROMPT_MANAGER = PromptManager(prompt_directory=str(_PROMPT_DIR))
_DOTPROMPT = DotpromptManager(prompt_directory=str(_PROMPT_DIR))


def _render_prompt_messages(prompt_id: str, prompt_variables: dict) -> list[dict]:
    rendered = _PROMPT_MANAGER.render(
        prompt_id=prompt_id,
        prompt_variables=prompt_variables,
    )
    return _DOTPROMPT._convert_to_messages(rendered)


class PromptGuardrail(CustomGuardrail):
    """
    Pre-call guardrail to render .prompt templates when prompt_id is supplied.
    Falls back to the original request if rendering fails.
    """

    def __init__(self, guardrail_name: str, event_hook: str, default_on: bool, **kwargs):
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
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            return data

        prompt_variables = dict(data.get("prompt_variables") or {})
        original_data = dict(data)

        try:
            template = _PROMPT_MANAGER.get_prompt(prompt_id=prompt_id)
            if template is None:
                return data

            messages = _render_prompt_messages(prompt_id, prompt_variables)
            data["messages"] = messages

            # Apply prompt-defined model if present
            template_model = getattr(template, "model", None)
            if template_model:
                data["model"] = template_model

            # Apply prompt-defined optional params if present
            optional_params = _DOTPROMPT._extract_optional_params(template)
            if isinstance(optional_params, dict):
                for k, v in optional_params.items():
                    if v is not None:
                        data[k] = v

            # Prevent downstream prompt managers from re-processing
            data.pop("prompt_id", None)
            data.pop("prompt_integration", None)
            data.pop("prompt_variables", None)

            logger.info(
                "prompt guardrail applied prompt_id=%s model=%s messages_len=%s",
                prompt_id,
                data.get("model"),
                len(messages),
            )

            return data
        except Exception:
            logger.exception("prompt guardrail failed; falling back to original request")
            return original_data
