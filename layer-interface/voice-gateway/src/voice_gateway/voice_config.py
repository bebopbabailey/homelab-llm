from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VoiceAlias:
    voice_id: str
    mode: str
    backend_speaker: str | None
    active: bool = True


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    default_voice_policy: str
    voices: tuple[VoiceAlias, ...]


DEFAULT_CONFIG = VoiceConfig(
    default_voice_policy="first_discovered_builtin",
    voices=(VoiceAlias(voice_id="default", mode="builtin", backend_speaker=None, active=True),),
)


class VoiceConfigError(RuntimeError):
    """Raised when the local voice config is invalid."""


def load_voice_config(path: Path) -> VoiceConfig:
    if not path.exists():
        return DEFAULT_CONFIG
    data = json.loads(path.read_text(encoding="utf-8"))
    default_voice_policy = data.get("default_voice_policy", "first_discovered_builtin")
    raw_voices = data.get("voices", [])
    voices: list[VoiceAlias] = []
    for raw_voice in raw_voices:
        mode = raw_voice.get("mode", "builtin")
        if mode != "builtin":
            raise VoiceConfigError("Phase 1 only supports builtin voice aliases")
        voices.append(
            VoiceAlias(
                voice_id=raw_voice["id"],
                mode=mode,
                backend_speaker=raw_voice.get("backend_speaker"),
                active=bool(raw_voice.get("active", True)),
            )
        )
    if not voices:
        return DEFAULT_CONFIG
    return VoiceConfig(default_voice_policy=default_voice_policy, voices=tuple(voices))


def resolve_voice(*, requested_voice: str, config: VoiceConfig, discovered_builtin_speakers: list[str]) -> tuple[str, str]:
    available = sorted(discovered_builtin_speakers)
    if not available:
        raise VoiceConfigError("No built-in XTTS speakers were discovered")

    aliases = {alias.voice_id: alias for alias in config.voices if alias.active}
    if requested_voice in aliases:
        alias = aliases[requested_voice]
        if alias.backend_speaker:
            if alias.backend_speaker not in available:
                raise VoiceConfigError(f"Configured built-in speaker '{alias.backend_speaker}' is unavailable")
            return alias.voice_id, alias.backend_speaker
        return alias.voice_id, available[0]

    if requested_voice in available:
        return requested_voice, requested_voice

    raise VoiceConfigError(f"Voice '{requested_voice}' is not available")
