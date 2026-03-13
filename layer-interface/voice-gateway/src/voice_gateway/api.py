from __future__ import annotations

import time
from os import unlink
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import FastAPI
from fastapi import BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from voice_gateway.logging import emit_log
from voice_gateway.models import ErrorBody, ErrorResponse, HealthResponse, SpeakerItem, SpeakersResponse, SpeechRequest
from voice_gateway.settings import Settings
from voice_gateway.tts_engine import DependencyBlockedError, TtsEngine, XttsEngine
from voice_gateway.voice_config import VoiceConfigError, load_voice_config, resolve_voice


def _build_engine(settings: Settings) -> TtsEngine:
    return XttsEngine(model_name=settings.tts_model, device=settings.tts_device)


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def create_app(*, settings: Settings | None = None, engine: TtsEngine | None = None) -> FastAPI:
    active_settings = settings or Settings()
    active_engine = engine or _build_engine(active_settings)
    app = FastAPI(title="Voice Gateway", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/health/readiness")
    def readiness() -> JSONResponse:
        request_id = str(uuid4())
        start = time.perf_counter()
        try:
            discovered = [speaker.name for speaker in active_engine.discover_builtin_speakers()]
            config = load_voice_config(active_settings.voice_config_path)
            resolved_voice, builtin_speaker = resolve_voice(
                requested_voice="default",
                config=config,
                discovered_builtin_speakers=discovered,
            )
            payload = {
                "status": "ready",
                "default_voice": resolved_voice,
                "resolved_builtin_speaker": builtin_speaker,
                "discovered_builtin_speakers": discovered,
            }
            emit_log(
                event="readiness",
                log_path=active_settings.log_path,
                request_id=request_id,
                route="/health/readiness",
                source="http",
                speaker_discovery_ms=round((time.perf_counter() - start) * 1000, 3),
                status="ready",
            )
            return JSONResponse(payload)
        except (DependencyBlockedError, VoiceConfigError) as exc:
            emit_log(
                event="readiness",
                log_path=active_settings.log_path,
                request_id=request_id,
                route="/health/readiness",
                source="http",
                status="blocked",
                error_code="readiness_blocked",
                exception_class=exc.__class__.__name__,
            )
            return _error_response(status_code=503, code="readiness_blocked", message=str(exc))

    @app.get("/v1/speakers", response_model=SpeakersResponse, responses={503: {"model": ErrorResponse}})
    def list_speakers() -> SpeakersResponse | JSONResponse:
        try:
            discovered = [speaker.name for speaker in active_engine.discover_builtin_speakers()]
            config = load_voice_config(active_settings.voice_config_path)
            default_voice, resolved_builtin = resolve_voice(
                requested_voice="default",
                config=config,
                discovered_builtin_speakers=discovered,
            )
        except DependencyBlockedError as exc:
            return _error_response(status_code=503, code="tts_backend_blocked", message=str(exc))
        except VoiceConfigError as exc:
            return _error_response(status_code=400, code="registry_invalid", message=str(exc))

        voices = [
            SpeakerItem(
                id=alias.voice_id,
                mode=alias.mode,
                backend_speaker=alias.backend_speaker or (resolved_builtin if alias.voice_id == default_voice else None),
                active=alias.active,
                available=(alias.backend_speaker in discovered) if alias.backend_speaker else alias.active,
            )
            for alias in config.voices
        ]
        return SpeakersResponse(
            default_voice=default_voice,
            discovered_builtin_speakers=discovered,
            voices=voices,
        )

    @app.post("/v1/audio/speech", responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def speech(request: SpeechRequest, background_tasks: BackgroundTasks):
        request_id = str(uuid4())
        total_start = time.perf_counter()
        if request.model != "xtts-v2":
            return _error_response(
                status_code=400,
                code="unsupported_model",
                message="model must be xtts-v2",
            )
        if request.response_format != "wav":
            return _error_response(
                status_code=400,
                code="invalid_response_format",
                message="response_format must be wav",
            )

        try:
            discovered = [speaker.name for speaker in active_engine.discover_builtin_speakers()]
            config = load_voice_config(active_settings.voice_config_path)
            speaker_id, builtin_speaker = resolve_voice(
                requested_voice=request.voice,
                config=config,
                discovered_builtin_speakers=discovered,
            )
            with NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                wav_path = Path(handle.name)
            result = active_engine.synthesize_to_wav(
                text=request.input,
                builtin_speaker=builtin_speaker,
                language=request.language or active_settings.default_language,
                output_path=wav_path,
            )
            total_ms = (time.perf_counter() - total_start) * 1000
            emit_log(
                event="speech",
                log_path=active_settings.log_path,
                request_id=request_id,
                source="http",
                route="/v1/audio/speech",
                model=request.model,
                speaker_id=speaker_id,
                resolved_builtin_speaker=builtin_speaker,
                language=request.language,
                input_chars=len(request.input),
                speaker_discovery_ms=result.speaker_discovery_ms,
                model_load_ms=result.model_load_ms,
                synth_ms=result.synth_ms,
                wav_write_ms=result.wav_write_ms,
                playback_ms=0.0,
                total_ms=round(total_ms, 3),
                output_bytes=result.output_bytes,
                status="ok",
                error_code=None,
                exception_class=None,
            )
            background_tasks.add_task(unlink, wav_path)
            return FileResponse(path=wav_path, media_type="audio/wav", filename="speech.wav")
        except DependencyBlockedError as exc:
            return _error_response(status_code=503, code="tts_backend_blocked", message=str(exc))
        except VoiceConfigError as exc:
            code = "speaker_not_found" if "not available" in str(exc) else "registry_invalid"
            return _error_response(status_code=400, code=code, message=str(exc))

    return app
