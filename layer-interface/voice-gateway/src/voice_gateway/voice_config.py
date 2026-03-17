from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VoiceAlias:
    voice_id: str
    backend_voice: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    default_voice_policy: str
    unknown_voice_policy: str
    fallback_voice_id: str
    voices: tuple[VoiceAlias, ...]


@dataclass(frozen=True, slots=True)
class VoiceResolution:
    requested_voice: str
    resolved_voice: str
    backend_voice: str
    warning: str | None = None


DEFAULT_CONFIG = VoiceConfig(
    default_voice_policy="configured_default",
    unknown_voice_policy="reject",
    fallback_voice_id="default",
    voices=(
        VoiceAlias(voice_id="default", backend_voice="af_heart", active=True),
        VoiceAlias(voice_id="alloy", backend_voice="af_heart", active=True),
    ),
)


class VoiceConfigError(RuntimeError):
    """Raised when the local voice config is invalid."""


def load_voice_config(path: Path) -> VoiceConfig:
    if not path.exists():
        return DEFAULT_CONFIG
    data = json.loads(path.read_text(encoding="utf-8"))
    default_voice_policy = str(data.get("default_voice_policy", "configured_default"))
    unknown_voice_policy = str(data.get("unknown_voice_policy", "reject"))
    if unknown_voice_policy not in {"reject", "fallback"}:
        raise VoiceConfigError("unknown_voice_policy must be 'reject' or 'fallback'")
    fallback_voice_id = str(data.get("fallback_voice_id", "default"))
    raw_voices = data.get("voices", [])
    voices: list[VoiceAlias] = []
    for raw_voice in raw_voices:
        backend_voice = raw_voice.get("backend_voice")
        if not isinstance(backend_voice, str) or not backend_voice.strip():
            raise VoiceConfigError("every voice alias must declare a non-empty backend_voice")
        voices.append(
            VoiceAlias(
                voice_id=str(raw_voice["id"]),
                backend_voice=backend_voice,
                active=bool(raw_voice.get("active", True)),
            )
        )
    if not voices:
        voices = list(DEFAULT_CONFIG.voices)
    aliases = {alias.voice_id for alias in voices if alias.active}
    if fallback_voice_id not in aliases:
        raise VoiceConfigError("fallback_voice_id must reference an active configured voice alias")
    return VoiceConfig(
        default_voice_policy=default_voice_policy,
        unknown_voice_policy=unknown_voice_policy,
        fallback_voice_id=fallback_voice_id,
        voices=tuple(voices),
    )


def resolve_voice_selection(*, requested_voice: str, config: VoiceConfig) -> VoiceResolution:
    aliases = {alias.voice_id: alias for alias in config.voices if alias.active}
    if requested_voice in aliases:
        alias = aliases[requested_voice]
        return VoiceResolution(
            requested_voice=requested_voice,
            resolved_voice=alias.voice_id,
            backend_voice=alias.backend_voice,
        )
    if config.unknown_voice_policy == "fallback":
        alias = aliases[config.fallback_voice_id]
        return VoiceResolution(
            requested_voice=requested_voice,
            resolved_voice=alias.voice_id,
            backend_voice=alias.backend_voice,
            warning=f"unknown voice '{requested_voice}' fell back to '{alias.voice_id}'",
        )
    raise VoiceConfigError(f"Voice '{requested_voice}' is not available")


def resolve_voice(*, requested_voice: str, config: VoiceConfig, discovered_builtin_speakers: list[str] | None = None) -> tuple[str, str]:
    resolution = resolve_voice_selection(requested_voice=requested_voice, config=config)
    return resolution.resolved_voice, resolution.backend_voice
