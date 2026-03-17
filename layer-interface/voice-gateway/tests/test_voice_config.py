from __future__ import annotations

import json
from pathlib import Path

import pytest

from voice_gateway.voice_config import load_voice_config, resolve_voice, resolve_voice_selection, VoiceConfigError


def test_default_config_maps_default_and_alloy_to_same_backend_voice(tmp_path: Path) -> None:
    config = load_voice_config(tmp_path / "missing.json")
    default_voice, default_backend = resolve_voice(requested_voice="default", config=config)
    alloy_voice, alloy_backend = resolve_voice(requested_voice="alloy", config=config)
    assert default_voice == "default"
    assert alloy_voice == "alloy"
    assert default_backend == alloy_backend == "af_heart"


def test_unknown_voice_rejects_by_default(tmp_path: Path) -> None:
    config = load_voice_config(tmp_path / "missing.json")
    with pytest.raises(VoiceConfigError):
        resolve_voice_selection(requested_voice="unknown", config=config)


def test_unknown_voice_can_fallback_with_warning(tmp_path: Path) -> None:
    config_path = tmp_path / "voices.json"
    config_path.write_text(
        json.dumps(
            {
                "unknown_voice_policy": "fallback",
                "fallback_voice_id": "default",
                "voices": [
                    {"id": "default", "backend_voice": "af_heart", "active": True},
                    {"id": "alloy", "backend_voice": "af_heart", "active": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    config = load_voice_config(config_path)
    resolution = resolve_voice_selection(requested_voice="unknown", config=config)
    assert resolution.resolved_voice == "default"
    assert resolution.backend_voice == "af_heart"
    assert resolution.warning is not None
