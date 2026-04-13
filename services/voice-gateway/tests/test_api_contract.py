from __future__ import annotations

import json

from fastapi.testclient import TestClient

from voice_gateway.api import create_app
from voice_gateway.backend import BackendHealth, BackendSpeechResult, BackendTranscriptionResult
from voice_gateway.settings import Settings


class FakeTtsBackend:
    def health(self) -> BackendHealth:
        return BackendHealth(status="ok", upstream_ms=5.0)

    def synthesize(self, *, text: str, backend_voice: str, response_format: str, speed: float) -> BackendSpeechResult:
        media_type = "audio/wav" if response_format == "wav" else "audio/mpeg"
        return BackendSpeechResult(
            content=b"fake-audio",
            media_type=media_type,
            output_bytes=len(b"fake-audio"),
            backend_model="speaches-ai/Kokoro-82M-v1.0-ONNX",
            backend_voice=backend_voice,
            upstream_ms=11.0,
        )

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
        payload = json.dumps({"text": "hello from fake backend"}).encode("utf-8")
        return BackendTranscriptionResult(
            content=payload,
            media_type="application/json",
            output_bytes=len(payload),
            backend_model="Systran/faster-distil-whisper-large-v3",
            upstream_ms=7.0,
        )

    def list_loaded_models(self):
        return {"models": ["speaches-ai/Kokoro-82M-v1.0-ONNX"]}, 3.0

    def list_local_models(self, *, task=None):
        del task
        return {
            "data": [
                {
                    "id": "speaches-ai/Kokoro-82M-v1.0-ONNX",
                    "voices": [{"id": "af_heart"}, {"id": "af_nova"}],
                }
            ]
        }, 4.0

    def list_registry_models(self, *, task=None):
        del task
        return {
            "data": [
                {
                    "id": "speaches-ai/Kokoro-82M-v1.0-ONNX",
                    "voices": [{"id": "af_heart"}, {"id": "af_nova"}],
                }
            ]
        }, 5.0

    def download_model(self, *, model_id):
        return {"status": "downloaded", "model_id": model_id}, 8.0

    def load_model(self, *, model_id):
        return {"status": "loaded", "model_id": model_id}, 6.0

    def unload_model(self, *, model_id):
        return {"status": "unloaded", "model_id": model_id}, 6.0

    def synthesize_with_model(self, *, model_id, text, backend_voice, response_format, speed):
        del model_id, text, backend_voice, speed
        media_type = "audio/wav" if response_format == "wav" else "audio/mpeg"
        return BackendSpeechResult(
            content=b"fake-preview",
            media_type=media_type,
            output_bytes=len(b"fake-preview"),
            backend_model="speaches-ai/Kokoro-82M-v1.0-ONNX",
            backend_voice="af_heart",
            upstream_ms=9.0,
        )


class FakeNativeSttBackend:
    def __init__(self) -> None:
        self.last_call: dict[str, object] | None = None

    def health(self) -> BackendHealth:
        return BackendHealth(status="ready", upstream_ms=3.0)

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
        self.last_call = {
            "file_name": file_name,
            "file_bytes": file_bytes,
            "content_type": content_type,
            "language": language,
            "prompt": prompt,
            "response_format": response_format,
            "temperature": temperature,
            "timestamp_granularities": timestamp_granularities,
        }
        if response_format == "text":
            content = b"hello from native stt"
            media_type = "text/plain"
        else:
            content = json.dumps({"text": "hello from native stt"}).encode("utf-8")
            media_type = "application/json"
        return BackendTranscriptionResult(
            content=content,
            media_type=media_type,
            output_bytes=len(content),
            backend_model="Systran/faster-distil-whisper-large-v3",
            upstream_ms=6.0,
        )


def _client(
    tmp_path,
    *,
    gateway_api_key: str | None = None,
    stt_backend: FakeNativeSttBackend | None = None,
) -> TestClient:
    stt_backend_api_base = "http://127.0.0.1:18081" if stt_backend is not None else None
    (tmp_path / "tts_models.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "kokoro-default",
                        "model_id": "speaches-ai/Kokoro-82M-v1.0-ONNX",
                        "family": "kokoro",
                        "status": "deployed",
                    }
                )
            ]
        )
        + "\n"
    )
    settings = Settings(
        voice_config_path=tmp_path / "voices.json",
        gateway_api_key=gateway_api_key,
        stt_backend_api_base=stt_backend_api_base,
        tts_registry_path=tmp_path / "tts_models.jsonl",
    )
    return TestClient(
        create_app(
            settings=settings,
            tts_backend=FakeTtsBackend(),
            stt_backend=stt_backend or FakeTtsBackend(),
        )
    )


def test_speech_endpoint_returns_audio(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "tts-1",
            "input": "hello",
            "voice": "default",
            "response_format": "wav",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content == b"fake-audio"


def test_speech_endpoint_rejects_unknown_voice(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "tts-1",
            "input": "hello",
            "voice": "unknown",
            "response_format": "wav",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "speaker_not_found"


def test_transcriptions_endpoint_returns_json(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/audio/transcriptions",
        data={"model": "whisper-1"},
        files={"file": ("sample.wav", b"wav-bytes", "audio/wav")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "hello from fake backend"


def test_native_stt_response_format_mapping_and_passthrough(tmp_path) -> None:
    native_stt = FakeNativeSttBackend()
    client = _client(tmp_path, stt_backend=native_stt)
    response = client.post(
        "/v1/audio/transcriptions",
        data={"model": "whisper-1", "language": "en", "prompt": "test", "response_format": "text"},
        files={"file": ("sample.wav", b"wav-bytes", "audio/wav")},
    )
    assert response.status_code == 200
    assert response.text == "hello from native stt"
    assert native_stt.last_call is not None
    assert native_stt.last_call["content_type"] == "audio/wav"
    assert native_stt.last_call["response_format"] == "text"
    assert native_stt.last_call["language"] == "en"
    assert native_stt.last_call["prompt"] == "test"


def test_native_stt_rejects_unsupported_transcription_format(tmp_path) -> None:
    client = _client(tmp_path, stt_backend=FakeNativeSttBackend())
    response = client.post(
        "/v1/audio/transcriptions",
        data={"model": "whisper-1", "response_format": "vtt"},
        files={"file": ("sample.wav", b"wav-bytes", "audio/wav")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_response_format"


def test_v1_routes_require_bearer_when_configured(tmp_path) -> None:
    client = _client(tmp_path, gateway_api_key="secret")
    response = client.get("/v1/models")
    assert response.status_code == 401
    authorized = client.get("/v1/models", headers={"Authorization": "Bearer secret"})
    assert authorized.status_code == 200


def test_ops_routes_require_bearer_when_configured(tmp_path) -> None:
    client = _client(tmp_path, gateway_api_key="secret")
    response = client.get("/ops/api/state")
    assert response.status_code == 401
    authorized = client.get("/ops/api/state", headers={"Authorization": "Bearer secret"})
    assert authorized.status_code == 200


def test_ops_curated_registry_route(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.get("/ops/api/registry/curated")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["models"][0]["id"] == "kokoro-default"


def test_ops_promotion_plan_returns_manual_commands(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/ops/api/promotion/plan",
        json={
            "backend_tts_model": "speaches-ai/Kokoro-82M-v1.0-ONNX",
            "fallback_voice_id": "default",
            "unknown_voice_policy": "reject",
            "include_default_alloy_aliases": True,
            "voice_ids": ["af_heart", "af_nova"],
        },
    )
    assert response.status_code == 200
    commands = response.json()["commands"]
    assert "VOICE_BACKEND_TTS_MODEL=speaches-ai/Kokoro-82M-v1.0-ONNX" in commands
    assert "/etc/voice-gateway/voices.json" in commands
    assert "systemctl restart voice-gateway.service" in commands
