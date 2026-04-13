from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_host() -> str:
    return os.environ.get("VOICE_GATEWAY_HOST", "127.0.0.1")


def _default_port() -> int | None:
    raw = os.environ.get("VOICE_GATEWAY_PORT")
    return int(raw) if raw else None


def _service_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class Settings:
    gateway_host: str = field(default_factory=_default_host)
    gateway_port: int | None = field(default_factory=_default_port)
    gateway_api_key: str | None = field(default_factory=lambda: os.environ.get("VOICE_GATEWAY_API_KEY"))
    voice_config_path: Path = field(
        default_factory=lambda: Path(os.environ.get("VOICE_CONFIG_PATH", "/etc/voice-gateway/voices.json"))
    )
    log_path: Path | None = field(
        default_factory=lambda: Path(os.environ["VOICE_LOG_PATH"]) if os.environ.get("VOICE_LOG_PATH") else None
    )
    log_level: str = field(default_factory=lambda: os.environ.get("VOICE_LOG_LEVEL", "INFO"))
    backend_api_base: str = field(
        default_factory=lambda: os.environ.get("VOICE_BACKEND_API_BASE", "http://127.0.0.1:8000/v1")
    )
    stt_backend_api_base: str | None = field(default_factory=lambda: os.environ.get("VOICE_STT_BACKEND_API_BASE"))
    backend_api_key: str | None = field(default_factory=lambda: os.environ.get("VOICE_BACKEND_API_KEY"))
    backend_timeout_seconds: float = field(
        default_factory=lambda: float(os.environ.get("VOICE_BACKEND_TIMEOUT_SECONDS", "60"))
    )
    public_stt_model: str = field(default_factory=lambda: os.environ.get("VOICE_PUBLIC_STT_MODEL", "whisper-1"))
    public_tts_model: str = field(default_factory=lambda: os.environ.get("VOICE_PUBLIC_TTS_MODEL", "tts-1"))
    backend_stt_model: str = field(
        default_factory=lambda: os.environ.get(
            "VOICE_BACKEND_STT_MODEL",
            "Systran/faster-distil-whisper-large-v3",
        )
    )
    backend_tts_model: str = field(
        default_factory=lambda: os.environ.get(
            "VOICE_BACKEND_TTS_MODEL",
            "speaches-ai/Kokoro-82M-v1.0-ONNX",
        )
    )
    default_language: str = field(default_factory=lambda: os.environ.get("VOICE_DEFAULT_LANGUAGE", "en"))
    tts_model: str = field(
        default_factory=lambda: os.environ.get("VOICE_TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    )
    tts_device: str = field(default_factory=lambda: os.environ.get("VOICE_TTS_DEVICE", "auto"))
    tts_registry_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("VOICE_TTS_REGISTRY_PATH", str(_service_root() / "registry" / "tts_models.jsonl"))
        )
    )
    deploy_manifest_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("VOICE_DEPLOY_MANIFEST_PATH", str(_service_root() / ".deploy-manifest.json"))
        )
    )

    def __post_init__(self) -> None:
        if self.gateway_port is not None and self.gateway_port <= 0:
            raise ValueError("VOICE_GATEWAY_PORT must be a positive integer")
        if self.backend_timeout_seconds <= 0:
            raise ValueError("VOICE_BACKEND_TIMEOUT_SECONDS must be positive")
        if self.gateway_host in {"127.0.0.1", "localhost", "0.0.0.0"}:
            return
        try:
            host_ip = ipaddress.ip_address(self.gateway_host)
        except ValueError as exc:
            raise ValueError("VOICE_GATEWAY_HOST must be loopback, 0.0.0.0, or a private IP address") from exc
        if not host_ip.is_private:
            raise ValueError("VOICE_GATEWAY_HOST must be a private IP address when not using loopback")
