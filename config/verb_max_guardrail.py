from __future__ import annotations

import os
import time
from typing import Any, Optional

import httpx

from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

MODEL_SMALL = "mlx-gpt-oss-20b-mxfp4-q4"
MODEL_LARGE = "mlx-gpt-oss-120b-mxfp4-q4"
VERB_MAX_PERSONAS = {"p-plan-max", "p-seek-max"}


def _mlx_env_prefix(model_id: str) -> str:
    return f"MLX_{model_id.upper().replace('-', '_')}"


def _mlx_model_value(model_id: str) -> str:
    return os.environ.get(f"{_mlx_env_prefix(model_id)}_MODEL", f"openai/{model_id}")


def _mlx_api_base(model_id: str) -> Optional[str]:
    return os.environ.get(f"{_mlx_env_prefix(model_id)}_API_BASE")


def _mlx_api_key(model_id: str) -> Optional[str]:
    return os.environ.get(f"{_mlx_env_prefix(model_id)}_API_KEY")


async def _post_json(url: str, headers: Optional[dict], payload: dict) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(url, headers=headers or {}, json=payload)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
    return None


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


class VerbMaxGuardrail(CustomGuardrail):
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
        if persona not in VERB_MAX_PERSONAS:
            return response

        if data.get("stream"):
            return response

        messages = data.get("messages")
        if not isinstance(messages, list):
            return response

        optillm_base = os.environ.get("OPTILLM_API_BASE", "http://127.0.0.1:4020/v1")
        optillm_key = os.environ.get("OPTILLM_API_KEY", "dummy")
        optillm_headers = {"Authorization": f"Bearer {optillm_key}"}

        base_payload = {
            "messages": messages,
            "temperature": data.get("temperature"),
            "top_p": data.get("top_p"),
            "max_tokens": data.get("max_tokens"),
        }

        heavy_payload = {
            **base_payload,
            "model": _mlx_model_value(MODEL_SMALL),
            "optillm_base_model": MODEL_SMALL,
            "optillm_approach": "plansearch&re2",
            "n": 1,
        }
        started = time.monotonic()
        heavy_resp = await _post_json(
            f"{optillm_base}/chat/completions",
            optillm_headers,
            heavy_payload,
        )
        heavy_time = time.monotonic() - started
        heavy_text = _extract_text(heavy_resp)
        choices = heavy_resp.get("choices") if isinstance(heavy_resp, dict) else []
        verbose_proxy_logger.info(
            "verb_max_guardrail: heavy model=%s approach=plansearch&re2 n_req=1 choices=%s latency=%.2fs",
            MODEL_SMALL,
            len(choices) if isinstance(choices, list) else 0,
            heavy_time,
        )
        if not heavy_text:
            return response

        light_payload = {
            **base_payload,
            "model": _mlx_model_value(MODEL_LARGE),
            "optillm_base_model": MODEL_LARGE,
            "optillm_approach": "re2",
            "messages": [
                {
                    "role": "system",
                    "content": "Return ONLY the refined response text. No preamble.",
                },
                {"role": "user", "content": heavy_text},
            ],
        }
        light_resp = await _post_json(
            f"{optillm_base}/chat/completions",
            optillm_headers,
            light_payload,
        )
        light_text = _extract_text(light_resp)
        if not light_text:
            return response

        if isinstance(response, dict):
            response = {**response}
            response["model"] = persona
            if isinstance(response.get("choices"), list) and response["choices"]:
                response["choices"][0] = {
                    **response["choices"][0],
                    "message": {"role": "assistant", "content": light_text},
                }
            return response

        return response
