from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ALLOWED_TOP_LEVEL_KEYS = frozenset(
    {"model", "messages", "temperature", "top_p", "max_tokens", "stream"}
)
REQUIRED_TOP_LEVEL_KEYS = frozenset(ALLOWED_TOP_LEVEL_KEYS)


@dataclass(frozen=True)
class OmlxRuntimeResponse:
    status_code: int
    body: dict[str, Any]
    elapsed_seconds: float
    request_bytes: int
    response_bytes: int


class OmlxRuntimeClientError(RuntimeError):
    failure_class = "adapter_error"


class OmlxRuntimeContractError(OmlxRuntimeClientError):
    failure_class = "adapter_contract_error"


class OmlxRuntimeTransportError(OmlxRuntimeClientError):
    failure_class = "adapter_transport_error"


class OmlxRuntimeParseError(OmlxRuntimeClientError):
    failure_class = "adapter_parse_error"


class OmlxRuntimeUpstreamHttpError(OmlxRuntimeClientError):
    failure_class = "upstream_http_error"

    def __init__(self, status_code: int, body: str):
        super().__init__(f"oMLX upstream returned HTTP {status_code}")
        self.status_code = status_code
        self.body = body


class OmlxRuntimeClient:
    """Thin non-stream chat-completions client for the oMLX specialized runtime."""

    def __init__(self, *, base_url: str, bearer_token: str, timeout_seconds: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds

    def chat_completions(self, payload: Mapping[str, Any]) -> OmlxRuntimeResponse:
        normalized = _validate_payload(payload)
        request_bytes = len(normalized)
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=normalized,
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connection": "close",
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise OmlxRuntimeUpstreamHttpError(exc.code, body) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise OmlxRuntimeTransportError(f"adapter transport failed: {exc}") from exc
        elapsed = time.monotonic() - started
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            snippet = raw[:400].decode("utf-8", errors="replace")
            raise OmlxRuntimeParseError(f"upstream returned invalid JSON: {snippet}") from exc
        if not isinstance(parsed, dict):
            raise OmlxRuntimeParseError("upstream returned non-object JSON")
        return OmlxRuntimeResponse(
            status_code=200,
            body=parsed,
            elapsed_seconds=elapsed,
            request_bytes=request_bytes,
            response_bytes=len(raw),
        )


def _validate_payload(payload: Mapping[str, Any]) -> bytes:
    if not isinstance(payload, Mapping):
        raise OmlxRuntimeContractError("payload must be a mapping")
    keys = set(payload.keys())
    missing = REQUIRED_TOP_LEVEL_KEYS - keys
    unknown = keys - ALLOWED_TOP_LEVEL_KEYS
    if missing:
        raise OmlxRuntimeContractError(f"payload missing required keys: {sorted(missing)}")
    if unknown:
        raise OmlxRuntimeContractError(f"payload contains unsupported keys: {sorted(unknown)}")
    if payload.get("stream") is not False:
        raise OmlxRuntimeContractError("phase 2 supports non-stream chat_completions only")
    if payload.get("temperature") != 0:
        raise OmlxRuntimeContractError("temperature must be 0 for the frozen contract")
    if payload.get("top_p") != 1:
        raise OmlxRuntimeContractError("top_p must be 1 for the frozen contract")
    if not isinstance(payload.get("max_tokens"), int) or payload["max_tokens"] <= 0:
        raise OmlxRuntimeContractError("max_tokens must be a positive integer")
    model = payload.get("model")
    if not isinstance(model, str) or not model.strip():
        raise OmlxRuntimeContractError("model must be a non-empty string")
    messages = payload.get("messages")
    if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes)) or len(messages) != 2:
        raise OmlxRuntimeContractError("messages must be a two-item sequence")
    expected_roles = ("system", "user")
    normalized_messages: list[dict[str, str]] = []
    for index, (message, role) in enumerate(zip(messages, expected_roles)):
        if not isinstance(message, Mapping):
            raise OmlxRuntimeContractError(f"messages[{index}] must be a mapping")
        if set(message.keys()) != {"role", "content"}:
            raise OmlxRuntimeContractError(
                f"messages[{index}] must contain only role and content"
            )
        if message.get("role") != role:
            raise OmlxRuntimeContractError(f"messages[{index}] role must be {role!r}")
        content = message.get("content")
        if not isinstance(content, str) or not content:
            raise OmlxRuntimeContractError(f"messages[{index}] content must be a non-empty string")
        normalized_messages.append({"role": role, "content": content})
    normalized_payload = {
        "model": model,
        "messages": normalized_messages,
        "temperature": 0,
        "top_p": 1,
        "max_tokens": payload["max_tokens"],
        "stream": False,
    }
    return json.dumps(normalized_payload, separators=(",", ":"), sort_keys=False).encode("utf-8")
