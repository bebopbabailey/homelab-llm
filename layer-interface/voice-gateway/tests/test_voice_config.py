from __future__ import annotations

import json
from pathlib import Path

from voice_gateway.voice_config import load_voice_config, resolve_voice


def test_default_config_resolves_first_discovered_builtin(tmp_path: Path) -> None:
    config = load_voice_config(tmp_path / "missing.json")
    speaker_id, builtin = resolve_voice(
        requested_voice="default",
        config=config,
        discovered_builtin_speakers=["speaker-b", "speaker-a"],
    )
    assert speaker_id == "default"
    assert builtin == "speaker-a"


def test_explicit_builtin_alias_resolves_requested_backend(tmp_path: Path) -> None:
    config_path = tmp_path / "voices.json"
    config_path.write_text(
        json.dumps(
            {
                "default_voice_policy": "first_discovered_builtin",
                "voices": [
                    {
                        "id": "default",
                        "mode": "builtin",
                        "backend_speaker": "speaker-b",
                        "active": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config = load_voice_config(config_path)
    speaker_id, builtin = resolve_voice(
        requested_voice="default",
        config=config,
        discovered_builtin_speakers=["speaker-a", "speaker-b"],
    )
    assert speaker_id == "default"
    assert builtin == "speaker-b"
