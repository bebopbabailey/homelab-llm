from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_host() -> str:
    return os.environ.get("VOICE_GATEWAY_HOST", "127.0.0.1")


def _default_port() -> int | None:
    raw = os.environ.get("VOICE_GATEWAY_PORT")
    return int(raw) if raw else None


@dataclass(slots=True)
class Settings:
    gateway_host: str = field(default_factory=_default_host)
    gateway_port: int | None = field(default_factory=_default_port)
    voice_config_path: Path = field(
        default_factory=lambda: Path(os.environ.get("VOICE_CONFIG_PATH", "/etc/voice-gateway/voices.json"))
    )
    log_path: Path | None = field(
        default_factory=lambda: Path(os.environ["VOICE_LOG_PATH"]) if os.environ.get("VOICE_LOG_PATH") else None
    )
    log_level: str = field(default_factory=lambda: os.environ.get("VOICE_LOG_LEVEL", "INFO"))
    tts_model: str = field(
        default_factory=lambda: os.environ.get("VOICE_TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    )
    tts_device: str = field(default_factory=lambda: os.environ.get("VOICE_TTS_DEVICE", "auto"))
    default_language: str = field(default_factory=lambda: os.environ.get("VOICE_DEFAULT_LANGUAGE", "en"))

    def __post_init__(self) -> None:
        if self.gateway_host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
            raise ValueError("Phase 1 Voice Gateway must stay loopback-published only")
        if self.gateway_port is not None and self.gateway_port <= 0:
            raise ValueError("VOICE_GATEWAY_PORT must be a positive integer")
