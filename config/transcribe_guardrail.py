from __future__ import annotations

import importlib.util
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.integrations.dotprompt.dotprompt_manager import DotpromptManager
from litellm.integrations.dotprompt.prompt_manager import PromptManager
from litellm.types.guardrails import GuardrailEventHooks


TASK_TRANSCRIBE_MODELS = {"task-transcribe", "task-transcribe-vivid"}
logger = logging.getLogger("transcribe_guardrail")
_TRACE_PATH = "/tmp/transcribe_guardrail_trace.jsonl"
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_PROMPT_MANAGER = PromptManager(prompt_directory=str(_PROMPT_DIR))
_DOTPROMPT = DotpromptManager(prompt_directory=str(_PROMPT_DIR))

try:
    from config.transcribe_utils import strip_punct_outside_words, strip_wrappers
except ModuleNotFoundError:
    _UTILS_PATH = Path(__file__).with_name("transcribe_utils.py")
    _UTILS_SPEC = importlib.util.spec_from_file_location("transcribe_utils", _UTILS_PATH)
    if _UTILS_SPEC is None or _UTILS_SPEC.loader is None:
        raise ImportError(f"Unable to load transcribe_utils from {_UTILS_PATH}")
    _UTILS_MODULE = importlib.util.module_from_spec(_UTILS_SPEC)
    _UTILS_SPEC.loader.exec_module(_UTILS_MODULE)
    strip_punct_outside_words = _UTILS_MODULE.strip_punct_outside_words
    strip_wrappers = _UTILS_MODULE.strip_wrappers

# Per your spec:
# model_ids:  task-transcribe, task-transcribe-vivid
# prompt_ids: task-transcribe, task-transcribe-vivid
PROMPT_ID_BY_MODEL = {
    "task-transcribe": "task-transcribe",
    "task-transcribe-vivid": "task-transcribe-vivid",
}

PROVIDER_MODEL_BY_ALIAS = {
    "task-transcribe": "openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct",
    "task-transcribe-vivid": "openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct",
}

DEFAULT_PARAMS_BY_MODEL = {
    "task-transcribe": {
        "temperature": 0.05,
        "top_p": 1.0,
        "max_tokens": 4096,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "stream": False,  # ensures post_call hook can run
    },
    "task-transcribe-vivid": {
        "temperature": 0.4,
        "top_p": 1.0,
        "max_tokens": 4096,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.2,
        "stream": False,
    },
}


def _extract_user_text(messages: Any) -> str:
    """Join all user message content into one transcript blob."""
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            parts.append(c.strip())
    return "\n\n".join(parts).strip()


_strip_wrappers = strip_wrappers
_preprocess_transcript = strip_punct_outside_words


def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    lowered = text.lower()
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _punctuation_required(text: str) -> bool:
    if not isinstance(text, str):
        return False
    length = len(text)
    if length < 80:
        return True
    punct = sum(text.count(ch) for ch in ".!?")
    required = max(1, length // 150)
    return punct >= required


async def _post_json(url: str, headers: dict, payload: dict) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
    return None


def _extract_chat_content(response: Any) -> Optional[str]:
    """OpenAI-style: choices[0].message.content"""
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass

    if not isinstance(response, dict):
        return None

    choices = response.get("choices")
    if not (isinstance(choices, list) and choices):
        return None

    first = choices[0]
    if not isinstance(first, dict):
        return None

    msg = first.get("message")
    if not isinstance(msg, dict):
        return None

    content = msg.get("content")
    return content if isinstance(content, str) else None


def _render_prompt_messages(prompt_id: str, prompt_variables: dict) -> list[dict]:
    rendered = _PROMPT_MANAGER.render(
        prompt_id=prompt_id,
        prompt_variables=prompt_variables,
    )
    return _DOTPROMPT._convert_to_messages(rendered)


class TranscribeGuardrail(CustomGuardrail):
    """
    One class, registered twice:
      - mode: pre_call  -> async_pre_call_hook
      - mode: post_call -> async_post_call_success_hook
    """

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
        model = data.get("model")
        if model not in TASK_TRANSCRIBE_MODELS:
            return data

        try:
            with open(_TRACE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "stage": "pre_call_input",
                    "model": model,
                    "prompt_id": PROMPT_ID_BY_MODEL[model],
                    "messages": data.get("messages"),
                    "prompt_variables": data.get("prompt_variables"),
                }, ensure_ascii=True) + "\n")
        except Exception:
            pass

        # 1) Use prompt manager with explicit prompt_id + variables
        prompt_id = PROMPT_ID_BY_MODEL[model]
        # Force provider model to avoid prompt manager overriding alias to a non-provider model
        data["model"] = PROVIDER_MODEL_BY_ALIAS[model]
        data.pop("ignore_prompt_manager_model", None)
        data.pop("ignore_prompt_manager_optional_params", None)
        data.pop("prompt_id", None)
        data.pop("prompt_integration", None)

        # 2) Extract transcript from incoming messages
        incoming_messages = data.get("messages") or []
        transcript = _extract_user_text(incoming_messages)
        transcript = _preprocess_transcript(transcript) if transcript else transcript

        # 3) Bind prompt variables (template supplies the user message)
        pv = dict(data.get("prompt_variables") or {})
        pv["user_message"] = transcript or ""
        if model == "task-transcribe-vivid":
            pv.setdefault("audience", "")
            pv.setdefault("tone", "")

        try:
            data["messages"] = _render_prompt_messages(prompt_id, pv)
            data.pop("prompt_variables", None)
        except Exception as exc:
            logger.exception("transcribe prompt render failed model=%s prompt_id=%s", model, prompt_id)

        # 5) Enforce params + non-streaming
        defaults = DEFAULT_PARAMS_BY_MODEL[model]
        for k, v in defaults.items():
            data[k] = v

        logger.info(
            "transcribe pre_call model=%s prompt_id=%s transcript_len=%s messages_len=%s prompt_vars=%s",
            model,
            prompt_id,
            len(transcript) if transcript else 0,
            len(data.get("messages") or []),
            sorted(pv.keys()),
        )

        try:
            with open(_TRACE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "stage": "pre_call_output",
                    "model": model,
                    "prompt_id": prompt_id,
                    "messages": data.get("messages"),
                    "prompt_variables": pv,
                }, ensure_ascii=True) + "\n")
        except Exception:
            pass

        return data

    async def async_post_call_success_hook(
            self,
            user_api_key_dict: Any,
            data: dict,
            response: Any,
    ) -> Any:
        model = data.get("model")
        if model not in TASK_TRANSCRIBE_MODELS:
            return response

        content = _extract_chat_content(response)
        if content is None:
            return response

        cleaned = _strip_wrappers(content)
        repaired = cleaned
        transcript = _extract_user_text(data.get("messages") or [])
        expected = _preprocess_transcript(transcript) if transcript else transcript
        normalized_in = _normalize_text(expected or "")
        normalized_out = _normalize_text(cleaned or "")
        validator_triggers = []
        if normalized_in and normalized_in == normalized_out:
            validator_triggers.append("no_op")
        if not _punctuation_required(cleaned):
            validator_triggers.append("missing_punct")

        repair_ran = False
        if validator_triggers:
            repair_ran = True
            api_base = data.get("api_base")
            api_key = data.get("api_key")
            provider_model = PROVIDER_MODEL_BY_ALIAS.get(model)
            if api_base and provider_model:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                repair_prompt = (
                    "REPAIR MODE. The output is invalid.\n"
                    "You MUST add sentence-ending punctuation and capitalization.\n"
                    "Returning the input unchanged is a failure.\n"
                    "Do NOT add or change words. Only punctuation/case/format and allowed disfluency removal.\n"
                    "Output ONLY the cleaned transcript text. No preamble."
                )
                payload = {
                    "model": provider_model,
                    "messages": [
                        {"role": "system", "content": repair_prompt},
                        {"role": "user", "content": expected or transcript or ""},
                    ],
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "max_tokens": data.get("max_tokens") or 4096,
                    "stream": False,
                }
                try:
                    started = time.monotonic()
                    repair_resp = await _post_json(f"{api_base}/chat/completions", headers, payload)
                    elapsed = time.monotonic() - started
                    repaired_text = _extract_chat_content(repair_resp)
                    if isinstance(repaired_text, str) and repaired_text.strip():
                        repaired = repaired_text
                    logger.info(
                        "transcribe repair model=%s triggers=%s latency=%.2fs",
                        model,
                        validator_triggers,
                        elapsed,
                    )
                except Exception:
                    logger.exception("transcribe repair failed model=%s", model)

        cleaned = _strip_wrappers(repaired)

        logger.info(
            "transcribe post_call model=%s content_len=%s cleaned_len=%s validators=%s repair=%s",
            model,
            len(content),
            len(cleaned) if isinstance(cleaned, str) else 0,
            validator_triggers,
            repair_ran,
        )

        # Normalize response dict and enforce "only transcript" output
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
                    msg["content"] = cleaned
                    # Strip extra fields if present
                    msg.pop("reasoning_content", None)
                    msg.pop("provider_specific_fields", None)

        return response
