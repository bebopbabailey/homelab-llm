from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.parse import quote

import httpx


@dataclass(frozen=True, slots=True)
class BackendHealth:
    status: str
    upstream_ms: float


@dataclass(frozen=True, slots=True)
class BackendSpeechResult:
    content: bytes
    media_type: str
    output_bytes: int
    backend_model: str
    backend_voice: str
    upstream_ms: float


@dataclass(frozen=True, slots=True)
class BackendTranscriptionResult:
    content: bytes
    media_type: str
    output_bytes: int
    backend_model: str
    upstream_ms: float


class BackendRequestError(RuntimeError):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _raise_for_error(response: httpx.Response) -> None:
    if not response.is_error:
        return
    code = "backend_error"
    message = response.text.strip() or f"backend returned HTTP {response.status_code}"
    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            code = str(error.get("code") or error.get("type") or code)
            message = str(error.get("message") or message)
        elif "detail" in payload:
            message = str(payload["detail"])
    raise BackendRequestError(status_code=response.status_code, code=code, message=message)


class SpeachesBackend:
    def __init__(
        self,
        *,
        api_base: str,
        timeout_seconds: float,
        api_key: str | None,
        stt_model: str,
        tts_model: str,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.stt_model = stt_model
        self.tts_model = tts_model

    def _root_url(self) -> str:
        if self.api_base.endswith("/v1"):
            return self.api_base[: -len("/v1")]
        return self.api_base

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def _request_json(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        payload: dict[str, object] | None = None,
    ) -> tuple[dict[str, object] | list[object], float]:
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.request(method, url, headers=self._headers(), params=params, json=payload)
        _raise_for_error(response)
        return response.json(), round((time.perf_counter() - start) * 1000, 3)

    @staticmethod
    def _media_type(response: httpx.Response, default: str) -> str:
        content_type = response.headers.get("content-type")
        if not content_type:
            return default
        return content_type.split(";", 1)[0].strip() or default

    def health(self) -> BackendHealth:
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self._root_url()}/health", headers=self._headers())
        _raise_for_error(response)
        try:
            payload = response.json()
            status = (
                str(payload.get("status", "ok")) if isinstance(payload, dict) else "ok"
            )
        except json.JSONDecodeError:
            status = "ok"
        return BackendHealth(
            status=status, upstream_ms=round((time.perf_counter() - start) * 1000, 3)
        )

    def synthesize(
        self,
        *,
        text: str,
        backend_voice: str,
        response_format: str,
        speed: float,
    ) -> BackendSpeechResult:
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base}/audio/speech",
                headers=self._headers(),
                json={
                    "model": self.tts_model,
                    "input": text,
                    "voice": backend_voice,
                    "response_format": response_format,
                    "speed": speed,
                },
            )
        _raise_for_error(response)
        return BackendSpeechResult(
            content=response.content,
            media_type=self._media_type(response, "application/octet-stream"),
            output_bytes=len(response.content),
            backend_model=self.tts_model,
            backend_voice=backend_voice,
            upstream_ms=round((time.perf_counter() - start) * 1000, 3),
        )

    def synthesize_with_model(
        self,
        *,
        model_id: str,
        text: str,
        backend_voice: str,
        response_format: str,
        speed: float,
    ) -> BackendSpeechResult:
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base}/audio/speech",
                headers=self._headers(),
                json={
                    "model": model_id,
                    "input": text,
                    "voice": backend_voice,
                    "response_format": response_format,
                    "speed": speed,
                },
            )
        _raise_for_error(response)
        return BackendSpeechResult(
            content=response.content,
            media_type=self._media_type(response, "application/octet-stream"),
            output_bytes=len(response.content),
            backend_model=model_id,
            backend_voice=backend_voice,
            upstream_ms=round((time.perf_counter() - start) * 1000, 3),
        )

    def list_local_models(self, *, task: str | None = None) -> tuple[dict[str, object], float]:
        params = {"task": task} if task else None
        payload, upstream_ms = self._request_json(method="GET", url=f"{self.api_base}/models", params=params)
        if not isinstance(payload, dict):
            raise BackendRequestError(status_code=502, code="invalid_backend_response", message="invalid /v1/models response")
        return payload, upstream_ms

    def list_registry_models(self, *, task: str | None = None) -> tuple[dict[str, object], float]:
        params = {"task": task} if task else None
        payload, upstream_ms = self._request_json(method="GET", url=f"{self.api_base}/registry", params=params)
        if not isinstance(payload, dict):
            raise BackendRequestError(
                status_code=502,
                code="invalid_backend_response",
                message="invalid /v1/registry response",
            )
        return payload, upstream_ms

    def list_loaded_models(self) -> tuple[dict[str, object], float]:
        payload, upstream_ms = self._request_json(method="GET", url=f"{self._root_url()}/api/ps")
        if not isinstance(payload, dict):
            raise BackendRequestError(status_code=502, code="invalid_backend_response", message="invalid /api/ps response")
        return payload, upstream_ms

    def download_model(self, *, model_id: str) -> tuple[dict[str, object], float]:
        encoded = quote(model_id, safe="")
        payload, upstream_ms = self._request_json(method="POST", url=f"{self.api_base}/models/{encoded}")
        if not isinstance(payload, dict):
            raise BackendRequestError(
                status_code=502,
                code="invalid_backend_response",
                message="invalid model download response",
            )
        return payload, upstream_ms

    def load_model(self, *, model_id: str) -> tuple[dict[str, object], float]:
        encoded = quote(model_id, safe="")
        payload, upstream_ms = self._request_json(method="POST", url=f"{self._root_url()}/api/ps/{encoded}")
        if not isinstance(payload, dict):
            raise BackendRequestError(status_code=502, code="invalid_backend_response", message="invalid model load response")
        return payload, upstream_ms

    def unload_model(self, *, model_id: str) -> tuple[dict[str, object], float]:
        encoded = quote(model_id, safe="")
        payload, upstream_ms = self._request_json(method="DELETE", url=f"{self._root_url()}/api/ps/{encoded}")
        if not isinstance(payload, dict):
            raise BackendRequestError(
                status_code=502,
                code="invalid_backend_response",
                message="invalid model unload response",
            )
        return payload, upstream_ms

    def transcribe(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        content_type: str | None,
        language: str | None,
        prompt: str | None,
        response_format: str | None,
        temperature: float | None,
        timestamp_granularities: list[str] | None,
    ) -> BackendTranscriptionResult:
        start = time.perf_counter()
        data: dict[str, object] = {"model": self.stt_model}
        if language:
            data["language"] = language
        if prompt:
            data["prompt"] = prompt
        if response_format:
            data["response_format"] = response_format
        if temperature is not None:
            data["temperature"] = str(temperature)
        if timestamp_granularities:
            data["timestamp_granularities[]"] = list(timestamp_granularities)
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base}/audio/transcriptions",
                headers=self._headers(),
                data=data,
                files=[
                    (
                        "file",
                        (
                            file_name,
                            file_bytes,
                            content_type or "application/octet-stream",
                        ),
                    )
                ],
            )
        _raise_for_error(response)
        default_media_type = "application/json"
        if response_format in {"text", "srt", "vtt"}:
            default_media_type = "text/plain"
        return BackendTranscriptionResult(
            content=response.content,
            media_type=self._media_type(response, default_media_type),
            output_bytes=len(response.content),
            backend_model=self.stt_model,
            upstream_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class NativeSttBackend:
    def __init__(self, *, api_base: str, timeout_seconds: float, model: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.model = model

    def health(self) -> BackendHealth:
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self.api_base}/health/readiness")
        _raise_for_error(response)
        try:
            payload = response.json()
            status = str(payload.get("status", "ok")) if isinstance(payload, dict) else "ok"
        except json.JSONDecodeError:
            status = "ok"
        return BackendHealth(status=status, upstream_ms=round((time.perf_counter() - start) * 1000, 3))

    @staticmethod
    def _response_media_type(response_format: str | None) -> str:
        if response_format == "text":
            return "text/plain"
        return "application/json"

    def transcribe(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        content_type: str | None,
        language: str | None,
        prompt: str | None,
        response_format: str | None,
        temperature: float | None,
        timestamp_granularities: list[str] | None,
    ) -> BackendTranscriptionResult:
        del file_name, temperature, timestamp_granularities
        params: dict[str, str] = {}
        if language:
            params["language"] = language
        if prompt:
            params["prompt"] = prompt
        start = time.perf_counter()
        headers = {"Content-Type": content_type or "application/octet-stream"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base}/transcribe",
                params=params,
                headers=headers,
                content=file_bytes,
            )
        _raise_for_error(response)
        payload = response.json()
        text = str(payload.get("text", "")) if isinstance(payload, dict) else ""
        if response_format == "text":
            content = text.encode("utf-8")
        else:
            content = json.dumps({"text": text}).encode("utf-8")
        return BackendTranscriptionResult(
            content=content,
            media_type=self._response_media_type(response_format),
            output_bytes=len(content),
            backend_model=self.model,
            upstream_ms=round((time.perf_counter() - start) * 1000, 3),
        )
