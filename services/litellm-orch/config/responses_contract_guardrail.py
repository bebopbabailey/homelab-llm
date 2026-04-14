from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from sys import stderr
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.types.guardrails import GuardrailEventHooks

logger = logging.getLogger("responses_contract_guardrail")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
_TRACE_PATH = Path("/tmp/litellm_responses_contract_guardrail.jsonl")
_TARGET_MODELS_DEFAULT = {"chatgpt-5"}
_REQUEST_CONTEXTS: dict[int, dict[str, Any]] = {}
_COUNTERS = Counter()
_LOCK = Lock()


def _parse_model_targets(raw: Any) -> set[str]:
    if not raw:
        return set(_TARGET_MODELS_DEFAULT)
    if isinstance(raw, str):
        return {item.strip().lower() for item in raw.split(",") if item.strip()}
    if isinstance(raw, (list, tuple, set)):
        out: set[str] = set()
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.add(item.strip().lower())
        return out or set(_TARGET_MODELS_DEFAULT)
    return set(_TARGET_MODELS_DEFAULT)


def _normalize_model_name(model: Any) -> str:
    if not isinstance(model, str):
        return ""
    normalized = model.strip().lower()
    if "/" in normalized:
        normalized = normalized.rsplit("/", 1)[-1]
    return normalized


def _is_target_model(model: Any, targets: set[str]) -> bool:
    return _normalize_model_name(model) in targets


def _to_loggable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_to_loggable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_loggable(v) for k, v in value.items()}
    return str(value)


def _response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        try:
            response = response.model_dump()
        except Exception:
            pass
    if isinstance(response, dict):
        return response
    return {}


def _extract_call_ids(response: Any) -> list[str]:
    body = _response_to_dict(response)
    out: list[str] = []
    for item in body.get("output") or []:
        if isinstance(item, dict):
            call_id = item.get("call_id")
            if isinstance(call_id, str) and call_id:
                out.append(call_id)
    return out


def emit_policy_event(event: dict[str, Any]) -> None:
    payload = json.dumps(_to_loggable(event), ensure_ascii=True, sort_keys=True)
    try:
        with _TRACE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
            handle.flush()
    except Exception:
        logger.exception("responses contract trace write failed payload=%s", payload)
    logger.info(payload)


def _record_summary() -> None:
    emit_policy_event(
        {
            "event_type": "policy_summary",
            "normalized_total": _COUNTERS.get("normalized", 0),
            "rejected_total": _COUNTERS.get("rejected", 0),
            "passthrough_total": _COUNTERS.get("passthrough", 0),
        }
    )


class ResponsesContractGuardrail(CustomGuardrail):
    def __init__(self, guardrail_name: str, event_hook: str, default_on: bool, **kwargs):
        self.target_models = _parse_model_targets(kwargs.get("target_models"))
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
        if not _is_target_model(data.get("model"), self.target_models):
            return data

        policy_request_id = uuid4().hex[:12]
        incoming_stream = data.get("stream")
        incoming_temperature = data.get("temperature")
        context = {
            "policy_request_id": policy_request_id,
            "lane_alias": _normalize_model_name(data.get("model")),
            "model": data.get("model"),
            "call_type": call_type,
            "incoming_stream": incoming_stream,
            "incoming_temperature": incoming_temperature,
        }

        with _LOCK:
            _REQUEST_CONTEXTS[id(data)] = context

        data["_responses_contract_policy_id"] = policy_request_id
        data["_responses_contract_call_type"] = call_type

        if call_type not in {"responses", "aresponses"}:
            with _LOCK:
                _COUNTERS["rejected"] += 1
            emit_policy_event(
                {
                    **context,
                    "event_type": "policy_decision",
                    "decision": "rejected",
                    "normalized_fields": [],
                    "rejection_reason": "responses_only_lane",
                    "outbound_stream": incoming_stream,
                    "outbound_temperature": incoming_temperature,
                }
            )
            _record_summary()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"model {context['lane_alias']} only accepts /v1/responses requests"
                ),
            )

        normalized_fields: list[str] = []
        if data.get("stream") is not False:
            data["stream"] = False
            normalized_fields.append("stream")
        if data.get("temperature") != 0.0:
            data["temperature"] = 0.0
            normalized_fields.append("temperature")

        decision = "normalized" if normalized_fields else "passthrough"
        with _LOCK:
            _COUNTERS[decision] += 1

        emit_policy_event(
            {
                **context,
                "event_type": "policy_decision",
                "decision": decision,
                "normalized_fields": normalized_fields,
                "rejection_reason": None,
                "outbound_stream": data.get("stream"),
                "outbound_temperature": data.get("temperature"),
            }
        )
        _record_summary()
        return data

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: Any,
        response: Any,
    ) -> Any:
        if not _is_target_model(data.get("model"), self.target_models):
            return response

        with _LOCK:
            context = _REQUEST_CONTEXTS.pop(id(data), None)

        body = _response_to_dict(response)
        emit_policy_event(
            {
                "event_type": "policy_result",
                "policy_request_id": data.pop("_responses_contract_policy_id", None)
                or (context or {}).get("policy_request_id")
                or uuid4().hex[:12],
                "lane_alias": (context or {}).get("lane_alias") or _normalize_model_name(data.get("model")),
                "call_type": data.pop("_responses_contract_call_type", None) or (context or {}).get("call_type"),
                "result": "success",
                "response_id": body.get("id"),
                "previous_response_id": body.get("previous_response_id"),
                "call_ids": _extract_call_ids(body),
                "tool_count": len(body.get("tools") or []),
                "http_status": 200,
            }
        )
        return response
