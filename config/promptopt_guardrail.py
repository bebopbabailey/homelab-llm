from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any, Optional

import httpx

from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

PROMPTOPT_MAX_PERSONA = "p-opt-max"
PROMPTOPT_BALANCED_PERSONA = "p-opt-balanced"
MODEL_SMALL = "mlx-gpt-oss-20b-mxfp4-q4"
MODEL_MEDIUM = "mlx-qwen3-next-80b-mxfp4-a3b-instruct"
MODEL_LARGE = "mlx-gpt-oss-120b-mxfp4-q4"


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


def _needs_cleanup(text: str) -> tuple[bool, str]:
    if not isinstance(text, str):
        return True, "non_string"
    lowered = text.lstrip().lower()
    if "```" in text:
        return True, "fence"
    if lowered.startswith(("here", "sure", "okay", "certainly", "of course")):
        return True, "preamble"
    if "prompt:" in lowered or "output:" in lowered:
        return True, "label"
    return False, "ok"


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    lowered = text.lower()
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _extract_user_text(messages: list) -> str:
    if not isinstance(messages, list):
        return ""
    parts = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            parts.append(str(msg.get("content", "")))
    return " ".join(parts).strip()


def _has_instructions_header(text: str) -> bool:
    for line in text.splitlines():
        if line.strip():
            return line.strip().startswith("INSTRUCTIONS:")
    return False


def _has_delimiter(text: str) -> bool:
    return "###" in text


def _count_bullets(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("-", "*", "•")):
            count += 1
        elif re.match(r"\d+\.", stripped):
            count += 1
    return count


def _scope_expansion_violation(original: str, output: str) -> bool:
    original_lower = original.lower()
    output_lower = output.lower()
    tokens = ["yaml", "json", "config", "snippet", "spec", "schema", "table", "cli"]
    if any(t in original_lower for t in tokens):
        return False
    requirement_phrases = [
        "must include",
        "must provide",
        "must output",
        "provide",
        "output format requires",
        "deliver",
        "return",
    ]
    if any(t in output_lower for t in tokens):
        for phrase in requirement_phrases:
            if phrase in output_lower:
                return True
    return False


def _prompt_stats(messages: list) -> tuple[int, int, bool]:
    if not isinstance(messages, list):
        return 0, 0, False
    user_text = " ".join(
        str(m.get("content", ""))
        for m in messages
        if isinstance(m, dict) and m.get("role") == "user"
    )
    if not user_text:
        return 0, 0, False
    lowered = user_text.lower()
    keywords = [
        "constraints",
        "must",
        "should",
        "do not",
        "output format",
        "format",
        "schema",
        "json",
        "steps",
        "phase",
        "phases",
        "workflow",
        "plan",
        "requirements",
        "rubric",
        "verify",
        "validate",
        "test",
        "edge case",
        "edge cases",
        "acceptance criteria",
    ]
    hits = sum(1 for k in keywords if k in lowered)
    long_prompt = len(user_text) >= 900
    return len(user_text), hits, long_prompt


async def _post_json(url: str, headers: Optional[dict], payload: dict) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(url, headers=headers or {}, json=payload)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
    return None


def _persona_model(persona: str) -> str:
    if persona == PROMPTOPT_BALANCED_PERSONA:
        return MODEL_MEDIUM
    return MODEL_LARGE


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
        if persona not in (PROMPTOPT_MAX_PERSONA, PROMPTOPT_BALANCED_PERSONA):
            return response

        if isinstance(metadata, dict) and metadata.get("skip_promptopt_reduce"):
            return response

        if data.get("stream"):
            return response

        initial_text = _extract_text(response)
        if not initial_text:
            return response

        messages = data.get("messages")
        if not isinstance(messages, list):
            return response
        original_prompt = _extract_user_text(messages)
        if not original_prompt:
            return response

        optillm_base = os.environ.get("OPTILLM_API_BASE", "http://127.0.0.1:4020/v1")
        optillm_key = os.environ.get("OPTILLM_API_KEY", "dummy")
        optillm_headers = {"Authorization": f"Bearer {optillm_key}"}

        prompt_len, keyword_hits, long_prompt = _prompt_stats(messages)
        if (prompt_len >= 900 and keyword_hits >= 3) or keyword_hits >= 5:
            complexity = "complex"
        elif prompt_len >= 600 or keyword_hits >= 3:
            complexity = "medium"
        else:
            complexity = "simple"
        candidate_payload_base = {
            "messages": messages,
            "temperature": data.get("temperature"),
            "top_p": data.get("top_p"),
            "max_tokens": data.get("max_tokens"),
        }

        async def _repair(
            model_id: str,
            system_prompt: str,
            current_output: str,
        ) -> Optional[str]:
            payload = {
                "model": _mlx_model_value(model_id),
                "optillm_base_model": model_id,
                "optillm_approach": "re2",
                "temperature": 0,
                "top_p": 1,
                "max_tokens": data.get("max_tokens") or 1200,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "original_prompt": original_prompt,
                                "current_output": current_output,
                            },
                            ensure_ascii=True,
                        ),
                    },
                ],
            }
            repair_resp = await _post_json(
                f"{optillm_base}/chat/completions",
                optillm_headers,
                payload,
            )
            return _extract_text(repair_resp) if repair_resp else None

        async def _cleanup(model_id: str, text: str) -> Optional[str]:
            cleanup_payload = {
                **candidate_payload_base,
                "model": _mlx_model_value(model_id),
                "optillm_base_model": model_id,
                "optillm_approach": "re2",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return ONLY the refined prompt text. No preamble, no commentary."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
            }
            cleanup_resp = await _post_json(
                f"{optillm_base}/chat/completions",
                optillm_headers,
                cleanup_payload,
            )
            return _extract_text(cleanup_resp) if cleanup_resp else None

        async def _validate_repair_cleanup(
            persona_name: str,
            text: str,
        ) -> str:
            validator_triggers = []
            normalized_input = _normalize_text(original_prompt)
            normalized_output = _normalize_text(text)
            if normalized_input and normalized_input == normalized_output:
                validator_triggers.append("A:no_op")
            if not _has_delimiter(text):
                validator_triggers.append("A:missing_delimiter")
            if not _has_instructions_header(text):
                validator_triggers.append("A:missing_instructions")
            if _scope_expansion_violation(original_prompt, text):
                validator_triggers.append("B:scope_expansion")
            if len(text) > 2200 or _count_bullets(text) > 25:
                validator_triggers.append("C:budget")

            repair_ran = False
            repaired_text = text
            if validator_triggers:
                repair_ran = True
                if any(t.startswith("A:") for t in validator_triggers):
                    repair_prompt = (
                        "Rewrite using the required template. Output only the refined prompt. "
                        "No preamble."
                    )
                elif any(t.startswith("B:") for t in validator_triggers):
                    repair_prompt = (
                        "Remove requirements not implied by the original. "
                        "Keep it minimal and within scope."
                    )
                else:
                    repair_prompt = (
                        "Compress. Keep only necessary instructions + template. "
                        "No extra deliverables."
                    )
                model_id = _persona_model(persona_name)
                repaired = await _repair(model_id, repair_prompt, text)
                if isinstance(repaired, str) and repaired.strip():
                    repaired_text = repaired

            needs_cleanup, cleanup_reason = _needs_cleanup(repaired_text)
            cleaned_text = repaired_text
            cleanup_ran = False
            if needs_cleanup:
                cleanup_ran = True
                model_id = _persona_model(persona_name)
                cleaned = await _cleanup(model_id, repaired_text)
                if isinstance(cleaned, str) and cleaned.strip():
                    cleaned_text = cleaned

            verbose_proxy_logger.info(
                "promptopt_guardrail: validators=%s repair=%s cleanup=%s output_len=%s",
                validator_triggers,
                repair_ran,
                cleanup_ran,
                len(cleaned_text or ""),
            )
            if cleanup_ran:
                verbose_proxy_logger.info(
                    "promptopt_guardrail: cleanup_reason=%s",
                    cleanup_reason,
                )
            return cleaned_text

        if persona == PROMPTOPT_BALANCED_PERSONA:
            cleaned_text = await _validate_repair_cleanup(persona, initial_text)
            if isinstance(response, dict):
                response = {**response}
                response["model"] = persona
                if isinstance(response.get("choices"), list) and response["choices"]:
                    response["choices"][0] = {
                        **response["choices"][0],
                        "message": {"role": "assistant", "content": cleaned_text},
                    }
            return response

        async def _candidate(model_id: str, approach: str, n: Optional[int] = None):
            payload = {
                **candidate_payload_base,
                "model": _mlx_model_value(model_id),
                "optillm_base_model": model_id,
                "optillm_approach": approach,
            }
            if n is not None:
                payload["n"] = n
            started = time.monotonic()
            resp = await _post_json(
                f"{optillm_base}/chat/completions",
                optillm_headers,
                payload,
            )
            elapsed = time.monotonic() - started
            choices = []
            finish_reason = None
            if isinstance(resp, dict):
                choices = resp.get("choices") or []
                if choices and isinstance(choices[0], dict):
                    finish_reason = choices[0].get("finish_reason")
            verbose_proxy_logger.info(
                "promptopt_guardrail: leg model=%s approach=%s n_req=%s choices=%s finish=%s latency=%.2fs",
                model_id,
                approach,
                n,
                len(choices),
                finish_reason,
                elapsed,
            )
            return _extract_text(resp) if resp else None

        if complexity == "complex":
            small_n, medium_n, large_approach = 6, 2, "plansearch&re2"
        elif complexity == "medium":
            small_n, medium_n, large_approach = 5, 2, "plansearch&re2"
        else:
            small_n, medium_n, large_approach = 4, 1, "re2"

        verbose_proxy_logger.info(
            "promptopt_guardrail: complexity=%s len=%s keyword_hits=%s n_small=%s n_medium=%s plansearch=%s",
            complexity,
            prompt_len,
            keyword_hits,
            small_n,
            medium_n,
            "plansearch" in large_approach,
        )

        small_task = asyncio.create_task(_candidate(MODEL_SMALL, "bon&re2", n=small_n))
        medium_task = asyncio.create_task(_candidate(MODEL_MEDIUM, "bon&re2", n=medium_n))
        tasks = [small_task, medium_task]
        if complexity != "simple":
            tasks.append(asyncio.create_task(_candidate(MODEL_LARGE, large_approach, n=1)))
        results = await asyncio.gather(*tasks)
        small_text = results[0]
        medium_text = results[1]
        large_text = results[2] if complexity != "simple" else None
        verbose_proxy_logger.info(
            "promptopt_guardrail: candidates small=%s medium=%s large=%s",
            bool(small_text),
            bool(medium_text),
            bool(large_text),
        )

        candidates = [
            {"id": "initial", "text": initial_text},
            {"id": "small", "text": small_text},
            {"id": "medium", "text": medium_text},
            {"id": "large", "text": large_text},
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
            "Output rules:\n"
            "- Return ONLY the chosen prompt text.\n"
            "- No preamble, no labels, no markdown fences.\n"
            "- Must include the ### delimiter if any candidate does.\n"
        )

        reducer_payload = {
            "model": _mlx_model_value(MODEL_MEDIUM),
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

        mlx_api_base = _mlx_api_base(MODEL_MEDIUM)
        if not mlx_api_base:
            return response
        mlx_headers = {}
        mlx_key = _mlx_api_key(MODEL_MEDIUM)
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

        cleaned_text = await _validate_repair_cleanup(persona, reduced_text)

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
