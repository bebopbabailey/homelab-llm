from __future__ import annotations

from fastapi.testclient import TestClient

from voice_gateway.native_stt_service import create_app


class FakeRuntime:
    def __init__(self) -> None:
        self.loaded = False
        self.request_count = 0

    def load(self) -> None:
        self.loaded = True

    def health_payload(self) -> dict[str, object]:
        return {"status": "ok", "service": "voice-gateway-native-stt", "requests": self.request_count}

    def readiness_payload(self) -> dict[str, object]:
        return {
            "status": "ready",
            "service": "voice-gateway-native-stt",
            "model_loaded_once": True,
            "load_count": 1,
            "request_count": self.request_count,
        }

    def transcribe(self, *, file_bytes: bytes, language: str | None, prompt: str | None) -> dict[str, object]:
        self.request_count += 1
        return {
            "text": "ok",
            "language": language,
            "prompt": prompt,
            "request_count": self.request_count,
        }


def test_health_and_readiness() -> None:
    runtime = FakeRuntime()
    client = TestClient(create_app(runtime))
    health = client.get("/health")
    readiness = client.get("/health/readiness")
    assert health.status_code == 200
    assert readiness.status_code == 200
    assert runtime.loaded is True
    assert readiness.json()["model_loaded_once"] is True


def test_transcribe_endpoint_accepts_raw_audio() -> None:
    runtime = FakeRuntime()
    client = TestClient(create_app(runtime))
    response = client.post(
        "/transcribe?language=en&prompt=hello",
        content=b"wav-bytes",
        headers={"Content-Type": "audio/wav"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "ok"
    assert payload["language"] == "en"
    assert payload["prompt"] == "hello"
