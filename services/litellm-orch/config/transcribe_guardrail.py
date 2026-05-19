from __future__ import annotations

import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.integrations.dotprompt.dotprompt_manager import DotpromptManager
from litellm.types.guardrails import GuardrailEventHooks


TASK_TRANSCRIBE_MODEL = "task-transcribe"
TASK_TRANSCRIBE_MODELS = {TASK_TRANSCRIBE_MODEL}
TASK_TRANSCRIBE_AUDIO_STT_MODEL = "voice-stt"
TASK_TRANSCRIBE_PROMPT_ID = "task-transcribe"
DEFAULT_OUTPUT_TOKENS = 8192
logger = logging.getLogger("transcribe_guardrail")
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_DOTPROMPT = DotpromptManager(prompt_directory=str(_PROMPT_DIR))

try:
    from config.transcribe_utils import prepare_transcript_text, strip_wrappers
except ModuleNotFoundError:
    _UTILS_PATH = Path(__file__).with_name("transcribe_utils.py")
    _UTILS_SPEC = importlib.util.spec_from_file_location("transcribe_utils", _UTILS_PATH)
    if _UTILS_SPEC is None or _UTILS_SPEC.loader is None:
        raise ImportError(f"Unable to load transcribe_utils from {_UTILS_PATH}")
    _UTILS_MODULE = importlib.util.module_from_spec(_UTILS_SPEC)
    _UTILS_SPEC.loader.exec_module(_UTILS_MODULE)
    prepare_transcript_text = _UTILS_MODULE.prepare_transcript_text
    strip_wrappers = _UTILS_MODULE.strip_wrappers


def _strip_provider_prefix(model: str) -> str:
    return model.rsplit("/", 1)[-1] if "/" in model else model


def _render_prompt_messages(prompt_id: str, prompt_variables: dict[str, Any]) -> list[dict[str, Any]]:
    compiled = _DOTPROMPT.compile_prompt(
        prompt_id=prompt_id,
        prompt_variables=prompt_variables,
        client_messages=[],
        dynamic_callback_params={},
    )
    messages = compiled.get("completed_messages") or compiled.get("prompt_template") or []
    return [dict(message) for message in messages if isinstance(message, dict)]


def _coerce_prompt_variables(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            logger.warning("transcribe audio ignored malformed prompt_variables")
            return {}
        if isinstance(parsed, dict):
            return dict(parsed)
    return {}


def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = int(value)
        except ValueError:
            return None
        if parsed > 0:
            return parsed
    return None


def _ensure_transcribe_prompt_variables(prompt_variables: dict[str, Any]) -> None:
    for key in ("audience", "tone"):
        value = prompt_variables.get(key)
        if value is None:
            prompt_variables[key] = ""
        elif not isinstance(value, str):
            prompt_variables[key] = str(value)


def _extract_user_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return "\n\n".join(parts).strip()


def _flatten_responses_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_responses_text(item) for item in value)
    if isinstance(value, dict):
        if value.get("type") in {"input_text", "output_text", "text"}:
            return _flatten_responses_text(value.get("text") or value.get("value"))
        if "content" in value:
            return _flatten_responses_text(value.get("content"))
        if "input" in value:
            return _flatten_responses_text(value.get("input"))
        return _flatten_responses_text(value.get("text"))
    return str(value)


def _extract_responses_input_text(input_value: Any) -> str:
    if isinstance(input_value, str):
        return input_value.strip()
    if not isinstance(input_value, list):
        return ""
    parts: list[str] = []
    for item in input_value:
        if not isinstance(item, dict):
            continue
        if item.get("role") != "user":
            continue
        text = _flatten_responses_text(item.get("content"))
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts).strip()


def _extract_chat_message(response: Any) -> dict[str, Any] | None:
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

    message = first.get("message")
    return message if isinstance(message, dict) else None


def _response_to_dict(response: Any) -> dict[str, Any] | None:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    return response if isinstance(response, dict) else None


def _extract_responses_output_text(response: Any) -> str | None:
    body = _response_to_dict(response)
    if not body:
        return None
    direct = _flatten_responses_text(body.get("output_text"))
    if direct.strip():
        return direct.strip()
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        text = _flatten_responses_text(item.get("content"))
        if text.strip():
            return text.strip()
    return None


def _extract_transcription_text(response: Any) -> str:
    if isinstance(response, str):
        return response.strip()
    if hasattr(response, "text"):
        text = getattr(response, "text")
        if isinstance(text, str):
            return text.strip()
    body = _response_to_dict(response)
    if not body:
        return ""
    text = body.get("text")
    if isinstance(text, str):
        return text.strip()
    return ""


def _set_chat_content(response: Any, content: str) -> Any:
    if hasattr(response, "model_dump"):
        response = response.model_dump()
    if not isinstance(response, dict):
        return response
    choices = response.get("choices")
    if not (isinstance(choices, list) and choices and isinstance(choices[0], dict)):
        return response
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return response
    message["content"] = content
    message.pop("reasoning", None)
    message.pop("reasoning_content", None)
    message.pop("provider_specific_fields", None)
    return response


def _set_responses_output_text(response: Any, content: str) -> Any:
    body = _response_to_dict(response)
    if not body:
        return response
    body["output"] = [
        {
            "id": body.get("id", "resp_task_alias"),
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": content, "annotations": []}],
        }
    ]
    body["output_text"] = content
    body.pop("reasoning", None)
    return body


def _minimal_audio_response_payload(response_id: str, output_text: str) -> dict[str, str]:
    return {"id": response_id, "output_text": output_text}


def _set_audio_output_text(response: Any, response_id: str, output_text: str) -> Any:
    payload = _minimal_audio_response_payload(response_id, output_text)
    if isinstance(response, dict):
        response.clear()
        response.update(payload)
        return response
    if hasattr(response, "model_dump"):
        response.model_dump = lambda *args, **kwargs: dict(payload)
    if hasattr(response, "json"):
        response.json = lambda *args, **kwargs: dict(payload)
    if hasattr(response, "model_dump_json"):
        response.model_dump_json = lambda *args, **kwargs: json.dumps(payload)
    for key, value in payload.items():
        try:
            setattr(response, key, value)
        except Exception:
            pass
    for key in ("text", "usage"):
        try:
            setattr(response, key, None)
        except Exception:
            pass
    return response


def _provider_config(data: dict[str, Any]) -> tuple[str, str, str | None]:
    api_base = os.getenv("LLMSTER_FAST_API_BASE", "")
    provider_model = os.getenv("LLMSTER_FAST_MODEL", "")
    if not api_base:
        api_base = str(data.get("_transcribe_audio_provider_api_base") or "")
    if not provider_model:
        provider_model = str(data.get("_transcribe_audio_provider_model") or "")
    api_key = os.getenv("LLMSTER_API_KEY") or None
    return api_base, provider_model, api_key


async def _post_responses(api_base: str, api_key: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "dummy":
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{api_base.rstrip('/')}/responses",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def _clean_audio_transcript(alias: str, transcript: str, data: dict[str, Any]) -> tuple[str, str]:
    api_base, provider_model, api_key = _provider_config(data)
    if not api_base:
        raise RuntimeError(f"{alias} audio cleanup requires provider api_base")
    if not provider_model:
        raise RuntimeError(f"{alias} audio cleanup requires provider model")

    transcript = _preprocess_transcript(transcript) if transcript else ""
    prompt_variables = _coerce_prompt_variables(data.get("_transcribe_audio_prompt_variables"))
    prompt_variables["user_message"] = transcript
    _ensure_transcribe_prompt_variables(prompt_variables)
    messages = _render_prompt_messages(TASK_TRANSCRIBE_PROMPT_ID, prompt_variables)
    max_output_tokens = (
        _coerce_positive_int(data.get("_transcribe_audio_max_output_tokens"))
        or DEFAULT_OUTPUT_TOKENS
    )
    body = await _post_responses(
        api_base,
        api_key,
        {
            "model": _strip_provider_prefix(provider_model),
            "input": messages,
            "reasoning": {"effort": "low"},
            "temperature": 0.0,
            "stream": False,
            "max_output_tokens": max_output_tokens,
        },
    )
    content = _extract_responses_output_text(body)
    response_id = str(body.get("id") or f"resp_{uuid4().hex}")
    if not content:
        logger.warning(
            "transcribe audio cleanup empty alias=%s fallback=preprocessed_transcript transcript_len=%s",
            alias,
            len(transcript),
        )
        return response_id, transcript
    cleaned = _strip_wrappers(content)
    if not cleaned:
        logger.warning(
            "transcribe audio cleanup stripped_empty alias=%s fallback=preprocessed_transcript transcript_len=%s",
            alias,
            len(transcript),
        )
        return response_id, transcript
    return response_id, cleaned


_strip_wrappers = strip_wrappers
_preprocess_transcript = prepare_transcript_text


class TranscribeGuardrail(CustomGuardrail):
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

        if call_type in {"transcription", "atranscription"}:
            data["_transcribe_audio_cleanup_alias"] = model
            data["_transcribe_audio_original_model"] = model
            prompt_variables = _coerce_prompt_variables(data.pop("prompt_variables", None))
            data["_transcribe_audio_prompt_variables"] = prompt_variables
            requested_output_tokens = _coerce_positive_int(data.pop("max_output_tokens", None))
            if requested_output_tokens is None:
                requested_output_tokens = DEFAULT_OUTPUT_TOKENS
            data["_transcribe_audio_max_output_tokens"] = requested_output_tokens
            data["model"] = TASK_TRANSCRIBE_AUDIO_STT_MODEL
            logger.info(
                "transcribe audio pre_call alias=%s stt_model=%s",
                model,
                data["model"],
            )
            return data

        if call_type in {"responses", "aresponses"}:
            transcript = _extract_responses_input_text(data.get("input"))
        else:
            transcript = _extract_user_text(data.get("messages") or [])
        transcript = _preprocess_transcript(transcript) if transcript else ""

        prompt_variables = _coerce_prompt_variables(data.get("prompt_variables"))
        prompt_variables["user_message"] = transcript
        _ensure_transcribe_prompt_variables(prompt_variables)

        if call_type in {"responses", "aresponses"}:
            if _coerce_positive_int(data.get("max_output_tokens")) is None:
                data["max_output_tokens"] = DEFAULT_OUTPUT_TOKENS
        else:
            if _coerce_positive_int(data.get("max_tokens")) is None:
                data["max_tokens"] = DEFAULT_OUTPUT_TOKENS

        data["_transcribe_text_cleanup_alias"] = TASK_TRANSCRIBE_MODEL
        data["prompt_id"] = TASK_TRANSCRIBE_PROMPT_ID
        data["prompt_variables"] = prompt_variables
        data["stream"] = False

        logger.info(
            "transcribe pre_call alias=%s prompt_id=%s transcript_len=%s prompt_vars=%s",
            model,
            data["prompt_id"],
            len(transcript),
            sorted(prompt_variables.keys()),
        )
        return data

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        model = data.get("model")
        alias = data.get("_transcribe_text_cleanup_alias") or model
        if alias not in TASK_TRANSCRIBE_MODELS:
            return response

        body = _response_to_dict(response)
        if body and body.get("object") == "response":
            content = _extract_responses_output_text(body)
            if not isinstance(content, str):
                return response
            cleaned = _strip_wrappers(content)
            logger.info(
                "transcribe post_call alias=%s route_model=%s content_len=%s cleaned_len=%s",
                alias,
                model,
                len(content),
                len(cleaned),
            )
            return _set_responses_output_text(body, cleaned)

        message = _extract_chat_message(response)
        if not isinstance(message, dict):
            return response

        content = message.get("content")
        if not isinstance(content, str):
            return response

        cleaned = _strip_wrappers(content)

        logger.info(
            "transcribe post_call alias=%s route_model=%s content_len=%s cleaned_len=%s",
            alias,
            model,
            len(content),
            len(cleaned),
        )
        return _set_chat_content(response, cleaned)

    async def async_post_call_response_headers_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
        request_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, str] | None:
        event_hook = (
            self.event_hook.value
            if isinstance(self.event_hook, GuardrailEventHooks)
            else self.event_hook
        )
        if event_hook != GuardrailEventHooks.post_call.value:
            return None

        alias = data.get("_transcribe_audio_cleanup_alias")
        if alias not in TASK_TRANSCRIBE_MODELS:
            return None

        raw_transcript = _extract_transcription_text(response)
        response_id = f"resp_{uuid4().hex}"
        if not raw_transcript:
            logger.error("transcribe audio post_call alias=%s empty_stt_transcript=true", alias)
            _set_audio_output_text(response, response_id, "")
            return None

        try:
            response_id, cleaned = await _clean_audio_transcript(alias, raw_transcript, data)
        except Exception:
            logger.exception("transcribe audio cleanup failed alias=%s", alias)
            _set_audio_output_text(response, response_id, "")
            return None

        logger.info(
            "transcribe audio post_call alias=%s raw_len=%s cleaned_len=%s",
            alias,
            len(raw_transcript),
            len(cleaned),
        )
        _set_audio_output_text(response, response_id, cleaned)
        return None
