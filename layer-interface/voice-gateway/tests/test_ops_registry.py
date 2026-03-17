from __future__ import annotations

import json

import pytest

from voice_gateway.ops_registry import OpsRegistryError, find_curated_model, load_curated_tts_registry


def test_load_curated_tts_registry_success(tmp_path) -> None:
    path = tmp_path / "tts_models.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "kokoro-default",
                        "model_id": "speaches-ai/Kokoro-82M-v1.0-ONNX",
                        "family": "kokoro",
                        "status": "deployed",
                        "recommended": True,
                    }
                ),
                json.dumps(
                    {
                        "id": "piper-lessac-high",
                        "model_id": "speaches-ai/piper-en_US-lessac-high",
                        "family": "piper",
                        "status": "candidate",
                    }
                ),
            ]
        )
        + "\n"
    )
    models = load_curated_tts_registry(path)
    assert len(models) == 2
    assert find_curated_model(models=models, selector="kokoro-default").model_id == "speaches-ai/Kokoro-82M-v1.0-ONNX"
    assert (
        find_curated_model(models=models, selector="speaches-ai/piper-en_US-lessac-high").registry_id
        == "piper-lessac-high"
    )


def test_load_curated_tts_registry_rejects_duplicate_ids(tmp_path) -> None:
    path = tmp_path / "tts_models.jsonl"
    row = {
        "id": "dup",
        "model_id": "speaches-ai/Kokoro-82M-v1.0-ONNX",
        "family": "kokoro",
        "status": "candidate",
    }
    path.write_text("\n".join([json.dumps(row), json.dumps(row)]) + "\n")
    with pytest.raises(OpsRegistryError):
        load_curated_tts_registry(path)
