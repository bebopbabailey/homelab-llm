from __future__ import annotations

import wave
from pathlib import Path

from fastapi.testclient import TestClient

from voice_gateway.api import create_app
from voice_gateway.settings import Settings
from voice_gateway.tts_engine import BuiltinSpeaker, EngineMetadata, SynthesisResult, TtsEngine


class FakeEngine(TtsEngine):
    def discover_builtin_speakers(self) -> list[BuiltinSpeaker]:
        return [BuiltinSpeaker(name="speaker-a"), BuiltinSpeaker(name="speaker-b")]

    def metadata(self) -> EngineMetadata:
        return EngineMetadata(model_name="xtts-v2", backend="fake")

    def synthesize_to_wav(
        self,
        *,
        text: str,
        builtin_speaker: str,
        language: str,
        output_path: Path,
    ) -> SynthesisResult:
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(b"\x00\x00" * 4800)
        return SynthesisResult(
            output_path=output_path,
            output_bytes=output_path.stat().st_size,
            builtin_speaker=builtin_speaker,
            language=language,
            model_load_ms=1.0,
            speaker_discovery_ms=1.0,
            synth_ms=2.0,
            wav_write_ms=1.0,
            cache_hit=False,
        )


def test_speech_endpoint_returns_wav(tmp_path: Path) -> None:
    settings = Settings(voice_config_path=tmp_path / "voices.json")
    client = TestClient(create_app(settings=settings, engine=FakeEngine()))
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "xtts-v2",
            "input": "hello",
            "voice": "default",
            "response_format": "wav",
            "language": "en",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert len(response.content) > 0


def test_speech_endpoint_rejects_non_wav(tmp_path: Path) -> None:
    settings = Settings(voice_config_path=tmp_path / "voices.json")
    client = TestClient(create_app(settings=settings, engine=FakeEngine()))
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "xtts-v2",
            "input": "hello",
            "voice": "default",
            "response_format": "mp3",
            "language": "en",
        },
    )
    assert response.status_code == 400
