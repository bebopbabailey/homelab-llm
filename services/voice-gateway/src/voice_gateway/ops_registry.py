from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CuratedTtsModel:
    registry_id: str
    model_id: str
    family: str
    status: str
    language_tags: tuple[str, ...]
    quality_tier: str | None
    recommended: bool
    voice_mode: str
    notes: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.registry_id,
            "model_id": self.model_id,
            "family": self.family,
            "status": self.status,
            "language_tags": list(self.language_tags),
            "quality_tier": self.quality_tier,
            "recommended": self.recommended,
            "voice_mode": self.voice_mode,
            "notes": self.notes,
        }


class OpsRegistryError(RuntimeError):
    pass


ALLOWED_STATUS = {"candidate", "approved", "deployed", "rejected"}


def _parse_line(*, payload: dict[str, object], line_number: int) -> CuratedTtsModel:
    registry_id = str(payload.get("id", "")).strip()
    model_id = str(payload.get("model_id", "")).strip()
    family = str(payload.get("family", "")).strip()
    status = str(payload.get("status", "")).strip()
    if not registry_id:
        raise OpsRegistryError(f"line {line_number}: missing id")
    if not model_id:
        raise OpsRegistryError(f"line {line_number}: missing model_id")
    if not family:
        raise OpsRegistryError(f"line {line_number}: missing family")
    if status not in ALLOWED_STATUS:
        raise OpsRegistryError(
            f"line {line_number}: status must be one of {sorted(ALLOWED_STATUS)}"
        )
    raw_langs = payload.get("language_tags", [])
    if isinstance(raw_langs, list):
        language_tags = tuple(str(value).strip() for value in raw_langs if str(value).strip())
    else:
        raise OpsRegistryError(f"line {line_number}: language_tags must be a list when present")
    quality_tier = payload.get("quality_tier")
    quality = str(quality_tier).strip() if quality_tier is not None else None
    notes_value = payload.get("notes")
    notes = str(notes_value).strip() if notes_value is not None else None
    voice_mode = str(payload.get("voice_mode", "builtin")).strip() or "builtin"
    recommended = bool(payload.get("recommended", False))
    return CuratedTtsModel(
        registry_id=registry_id,
        model_id=model_id,
        family=family,
        status=status,
        language_tags=language_tags,
        quality_tier=quality,
        recommended=recommended,
        voice_mode=voice_mode,
        notes=notes,
    )


def load_curated_tts_registry(path: Path) -> list[CuratedTtsModel]:
    if not path.exists():
        raise OpsRegistryError(f"missing curated tts registry: {path}")
    models: list[CuratedTtsModel] = []
    seen_registry_ids: set[str] = set()
    seen_model_ids: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise OpsRegistryError(
                f"line {line_number}: invalid json ({exc.msg} at column {exc.colno})"
            ) from exc
        if not isinstance(payload, dict):
            raise OpsRegistryError(f"line {line_number}: each JSONL row must be an object")
        item = _parse_line(payload=payload, line_number=line_number)
        if item.registry_id in seen_registry_ids:
            raise OpsRegistryError(f"line {line_number}: duplicate id '{item.registry_id}'")
        if item.model_id in seen_model_ids:
            raise OpsRegistryError(f"line {line_number}: duplicate model_id '{item.model_id}'")
        seen_registry_ids.add(item.registry_id)
        seen_model_ids.add(item.model_id)
        models.append(item)
    if not models:
        raise OpsRegistryError("curated tts registry is empty")
    return models


def find_curated_model(*, models: list[CuratedTtsModel], selector: str) -> CuratedTtsModel:
    key = selector.strip()
    for item in models:
        if item.registry_id == key or item.model_id == key:
            return item
    raise OpsRegistryError(f"unknown curated model selector: {selector}")
