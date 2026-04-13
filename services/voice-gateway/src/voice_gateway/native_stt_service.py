from __future__ import annotations

import argparse
import io
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ctranslate2
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

from voice_gateway.logging import emit_log


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass(slots=True)
class NativeRuntimeConfig:
    host: str = _env_str("NATIVE_STT_HOST", "127.0.0.1")
    port: int = _env_int("NATIVE_STT_PORT", 18081)
    model: str = _env_str("NATIVE_STT_MODEL", "Systran/faster-distil-whisper-large-v3")
    device: str = _env_str("NATIVE_STT_DEVICE", "cuda")
    compute_type: str = _env_str("NATIVE_STT_COMPUTE_TYPE", "float16")
    expected_ct2_version: str = _env_str("NATIVE_STT_CT2_VERSION", "4.7.1")
    expected_fw_version: str = _env_str("NATIVE_STT_FW_VERSION", "1.1.1")
    expected_source_ref: str = _env_str(
        "NATIVE_STT_CTRANSLATE2_SOURCE_REF", "226c95d94e660c48b11c62e108886b7ef76d589d"
    )
    expected_ct2_prefix: str = _env_str("NATIVE_STT_CT2_PREFIX", "/home/christopherbailey/stt-native-lab/ct2-prefix")


class NativeSttRuntime:
    def __init__(self, config: NativeRuntimeConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._ready = False
        self._ready_error: str | None = None
        self._ready_since_unix: float | None = None
        self._load_count = 0
        self._request_count = 0
        self._model: WhisperModel | None = None
        self._proof: dict[str, Any] = {}

    @staticmethod
    def _require_exact(name: str, observed: str, expected: str) -> None:
        if observed != expected:
            raise RuntimeError(f"{name} mismatch: expected {expected}, got {observed}")

    def load(self) -> None:
        with self._lock:
            if self._ready:
                return
            started = time.perf_counter()
            try:
                import faster_whisper

                fw_version = str(getattr(faster_whisper, "__version__", "unknown"))
                ct2_version = str(ctranslate2.__version__)
                cuda_device_count = int(ctranslate2.get_cuda_device_count())
                ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
                ct2_prefix = self._config.expected_ct2_prefix
                ct2_file = str(Path(ctranslate2.__file__).resolve())

                self._require_exact("ctranslate2", ct2_version, self._config.expected_ct2_version)
                self._require_exact("faster-whisper", fw_version, self._config.expected_fw_version)
                if cuda_device_count < 1:
                    raise RuntimeError("cuda_device_count must be >= 1")
                ld_paths = [entry for entry in ld_library_path.split(":") if entry]
                expected_lib_path = str(Path(ct2_prefix) / "lib")
                if ct2_prefix not in ld_paths and expected_lib_path not in ld_paths:
                    raise RuntimeError(f"LD_LIBRARY_PATH missing expected CTranslate2 prefix: {ct2_prefix}")

                model = WhisperModel(
                    self._config.model,
                    device=self._config.device,
                    device_index=0,
                    compute_type=self._config.compute_type,
                )

                self._model = model
                self._load_count += 1
                self._ready = True
                self._ready_error = None
                self._ready_since_unix = time.time()
                self._proof = {
                    "ctranslate2_version": ct2_version,
                    "ctranslate2_file": ct2_file,
                    "faster_whisper_version": fw_version,
                    "ctranslate2_source_ref": self._config.expected_source_ref,
                    "ctranslate2_prefix": ct2_prefix,
                    "model": self._config.model,
                    "device": self._config.device,
                    "compute_type": self._config.compute_type,
                    "cuda_device_count": cuda_device_count,
                    "load_count": self._load_count,
                    "load_ms": round((time.perf_counter() - started) * 1000, 3),
                }
                emit_log(event="native_stt_startup", log_path=None, status="ready", **self._proof)
            except Exception as exc:  # pragma: no cover - startup failures exercised via readiness checks
                self._ready = False
                self._ready_error = str(exc)
                self._proof = {}
                emit_log(
                    event="native_stt_startup",
                    log_path=None,
                    status="blocked",
                    error_code="native_stt_startup_failed",
                    exception_class=exc.__class__.__name__,
                    message=str(exc),
                )
                raise

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "voice-gateway-native-stt",
            "requests": self._request_count,
        }

    def readiness_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "ready" if self._ready else "blocked",
            "service": "voice-gateway-native-stt",
            "model_loaded_once": self._load_count == 1,
            "load_count": self._load_count,
            "request_count": self._request_count,
            "ready_since_unix": self._ready_since_unix,
            **self._proof,
        }
        if self._ready_error:
            payload["error"] = self._ready_error
        return payload

    def transcribe(self, *, file_bytes: bytes, language: str | None, prompt: str | None) -> dict[str, Any]:
        if not self._ready or self._model is None:
            raise RuntimeError("native stt runtime is not ready")
        if not file_bytes:
            raise ValueError("empty audio payload")
        audio = decode_audio(io.BytesIO(file_bytes), sampling_rate=16000)
        segments, info = self._model.transcribe(
            audio,
            language=language,
            initial_prompt=prompt,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        text = "".join(segment.text for segment in segments).strip()
        self._request_count += 1
        return {
            "text": text,
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None),
            "model_loaded_once": self._load_count == 1,
            "load_count": self._load_count,
            "request_count": self._request_count,
        }


def create_app(runtime: NativeSttRuntime) -> FastAPI:
    app = FastAPI(title="Voice Gateway Native STT", version="0.1.0")

    @app.on_event("startup")
    def startup_event() -> None:
        runtime.load()

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse(runtime.health_payload())

    @app.get("/health/readiness")
    def readiness() -> JSONResponse:
        payload = runtime.readiness_payload()
        status_code = 200 if payload.get("status") == "ready" else 503
        return JSONResponse(payload, status_code=status_code)

    @app.post("/transcribe")
    async def transcribe(request: Request, language: str | None = None, prompt: str | None = None) -> JSONResponse:
        try:
            file_bytes = await request.body()
            payload = runtime.transcribe(file_bytes=file_bytes, language=language, prompt=prompt)
            return JSONResponse(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run localhost native STT wrapper")
    parser.add_argument("--host", default=_env_str("NATIVE_STT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=_env_int("NATIVE_STT_PORT", 18081))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = NativeRuntimeConfig(host=args.host, port=args.port)
    runtime = NativeSttRuntime(config=config)
    uvicorn.run(create_app(runtime), host=config.host, port=config.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
