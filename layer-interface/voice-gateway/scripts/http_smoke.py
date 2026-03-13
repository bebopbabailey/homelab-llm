from __future__ import annotations

import json
import tempfile
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from voice_gateway.api import create_app
from voice_gateway.settings import Settings
from voice_gateway.tts_engine import BuiltinSpeaker, EngineMetadata, SynthesisResult, TtsEngine


class SmokeEngine(TtsEngine):
    def discover_builtin_speakers(self) -> list[BuiltinSpeaker]:
        return [BuiltinSpeaker(name="speaker-a"), BuiltinSpeaker(name="speaker-b")]

    def metadata(self) -> EngineMetadata:
        return EngineMetadata(model_name="xtts-v2", backend="smoke")

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
            wav_file.writeframes(b"\x00\x00" * 2400)
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


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = Settings(
            voice_config_path=Path(temp_dir) / "voices.json",
            gateway_host="127.0.0.1",
            gateway_port=18080,
        )
        app = create_app(settings=settings, engine=SmokeEngine())
        client = TestClient(app)

        health_response = client.get("/health")
        readiness_response = client.get("/health/readiness")
        speakers_response = client.get("/v1/speakers")
        speech_response = client.post(
            "/v1/audio/speech",
            json={
                "model": "xtts-v2",
                "input": "phase one http smoke",
                "voice": "default",
                "response_format": "wav",
                "language": "en",
            },
        )

        summary = {
            "health": health_response.status_code,
            "readiness": readiness_response.status_code,
            "speakers": speakers_response.status_code,
            "speech": speech_response.status_code,
            "content_type": speech_response.headers.get("content-type"),
            "output_bytes": len(speech_response.content),
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
