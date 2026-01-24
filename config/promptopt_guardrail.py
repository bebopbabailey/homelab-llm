from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

import httpx

from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

PROMPTOPT_MAX_PERSONA = "p-opt-max"


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


class PromptOptMaxGuardrail(CustomGuardrail):
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
        verbose_proxy_logger.info(
            "promptopt_guardrail: post_call start, keys=%s",
            list(data.keys()),
        )
        metadata = data.get("metadata") or data.get("litellm_metadata") or {}
        persona = metadata.get("persona")
        verbose_proxy_logger.info(
            "promptopt_guardrail: persona=%s guardrails=%s",
            persona,
            data.get("guardrails"),
        )
        if persona != PROMPTOPT_MAX_PERSONA:
            return response

        if isinstance(metadata, dict) and metadata.get("skip_promptopt_reduce"):
            return response

        if data.get("stream"):
            return response

        base_model = data.get("optillm_base_model")
        if not isinstance(base_model, str):
            return response

        initial_text = _extract_text(response)
        if not initial_text:
            return response

        optillm_base = os.environ.get("OPTILLM_API_BASE", "http://127.0.0.1:4020/v1")
        optillm_key = os.environ.get("OPTILLM_API_KEY", "dummy")
        optillm_headers = {"Authorization": f"Bearer {optillm_key}"}

        messages = data.get("messages")
        if not isinstance(messages, list):
            return response

        candidate_payload = {
            "model": _mlx_model_value(base_model),
            "messages": messages,
            "optillm_base_model": base_model,
            "temperature": data.get("temperature"),
            "top_p": data.get("top_p"),
            "max_tokens": data.get("max_tokens"),
        }

        async def _candidate(approach: str) -> Optional[str]:
            payload = {**candidate_payload, "optillm_approach": approach}
            resp = await _post_json(
                f"{optillm_base}/chat/completions",
                optillm_headers,
                payload,
            )
            return _extract_text(resp) if resp else None

        leap_task = asyncio.create_task(_candidate("leap"))
        plan_task = asyncio.create_task(_candidate("plansearch"))
        leap_text, plan_text = await asyncio.gather(leap_task, plan_task)
        verbose_proxy_logger.info(
            "promptopt_guardrail: candidates leap=%s plansearch=%s",
            bool(leap_text),
            bool(plan_text),
        )

        candidates = [
            {"id": "re2", "text": initial_text},
            {"id": "leap", "text": leap_text},
            {"id": "plansearch", "text": plan_text},
        ]
        candidates = [c for c in candidates if isinstance(c.get("text"), str)]
        if len(candidates) < 2:
            return response

        reducer_prompt = (
            "You are a prompt selection reducer. Choose the single best candidate prompt.\n\n"
            "Rubric (score 0-5 each):\n"
            "1) Preserves user intent/constraints (no new requirements).\n"
            "2) Clear role and success criteria.\n"
            "3) Explicit output format and delimiters.\n"
            "4) Removes ambiguity/contradictions.\n"
            "5) Concise and directly usable.\n\n"
            "Input JSON contains the original prompt and candidates. "
            "Output ONLY the chosen candidate prompt text."
        )

        reducer_payload = {
            "model": _mlx_model_value(base_model),
            "messages": [
                {"role": "system", "content": reducer_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "original_messages": messages,
                            "candidates": candidates,
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 4000,
        }

        mlx_api_base = _mlx_api_base(base_model)
        if not mlx_api_base:
            return response
        mlx_headers = {}
        mlx_key = _mlx_api_key(base_model)
        if mlx_key:
            mlx_headers["Authorization"] = f"Bearer {mlx_key}"

        reducer_resp = await _post_json(
            f"{mlx_api_base}/chat/completions",
            mlx_headers,
            reducer_payload,
        )
        reduced_text = _extract_text(reducer_resp)
        if not reduced_text:
            return response

        cleanup_payload = {
            **candidate_payload,
            "optillm_approach": "re2",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return ONLY the refined prompt text. No preamble, no commentary."
                    ),
                },
                {"role": "user", "content": reduced_text},
            ],
        }
        cleanup_resp = await _post_json(
            f"{optillm_base}/chat/completions",
            optillm_headers,
            cleanup_payload,
        )
        cleaned_text = _extract_text(cleanup_resp) or reduced_text

        if isinstance(response, dict):
            response = {**response}
            response["model"] = PROMPTOPT_MAX_PERSONA
            if isinstance(response.get("choices"), list) and response["choices"]:
                response["choices"][0] = {
                    **response["choices"][0],
                    "message": {"role": "assistant", "content": cleaned_text},
                }
            return response

        return response
