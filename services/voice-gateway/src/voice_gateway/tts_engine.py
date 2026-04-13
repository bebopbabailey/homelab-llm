from __future__ import annotations

import time
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BuiltinSpeaker:
    name: str


@dataclass(frozen=True, slots=True)
class EngineMetadata:
    model_name: str
    backend: str


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    output_path: Path
    output_bytes: int
    builtin_speaker: str
    language: str
    model_load_ms: float
    speaker_discovery_ms: float
    synth_ms: float
    wav_write_ms: float
    cache_hit: bool


class TtsEngine(Protocol):
    def metadata(self) -> EngineMetadata: ...
    def discover_builtin_speakers(self) -> list[BuiltinSpeaker]: ...
    def synthesize_to_wav(
        self,
        *,
        text: str,
        builtin_speaker: str,
        language: str,
        output_path: Path,
    ) -> SynthesisResult: ...


class DependencyBlockedError(RuntimeError):
    """Raised when XTTS runtime dependencies are not available yet."""


class XttsEngine:
    def __init__(self, *, model_name: str, device: str) -> None:
        self._model_name = model_name
        self._device = device
        self._tts = None
        self._loaded_device: str | None = None

    def metadata(self) -> EngineMetadata:
        return EngineMetadata(model_name=self._model_name, backend="coqui-xtts")

    def _runtime(self):
        try:
            import torch
            from TTS.api import TTS as CoquiTTS
        except Exception as exc:  # pragma: no cover - exercised in runtime image
            raise DependencyBlockedError(
                "XTTS runtime dependencies are unavailable. Use the repo-tracked "
                "wrapper-proof container built from the proven runtime image."
            ) from exc
        return torch, CoquiTTS

    def _resolve_device(self) -> str:
        torch, _ = self._runtime()
        if self._device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return self._device

    def _ensure_model(self, *, move_to_target: bool) -> tuple[object, float, bool]:
        _, coqui_tts = self._runtime()
        target_device = self._resolve_device()
        start = time.perf_counter()
        cache_hit = self._tts is not None

        if self._tts is None:
            self._tts = coqui_tts(model_name=self._model_name, progress_bar=False)
            self._loaded_device = "cpu"

        if move_to_target and target_device != self._loaded_device:
            self._tts = self._tts.to(target_device)
            self._loaded_device = target_device

        elapsed_ms = (time.perf_counter() - start) * 1000
        return self._tts, elapsed_ms, cache_hit

    @staticmethod
    def _builtin_speakers(tts: object) -> list[BuiltinSpeaker]:
        raw_speakers = getattr(tts, "speakers", None) or []
        normalized = sorted({speaker.strip() for speaker in raw_speakers if isinstance(speaker, str) and speaker.strip()})
        return [BuiltinSpeaker(name=speaker) for speaker in normalized]

    def discover_builtin_speakers(self) -> list[BuiltinSpeaker]:
        tts, _, _ = self._ensure_model(move_to_target=False)
        return self._builtin_speakers(tts)

    def synthesize_to_wav(
        self,
        *,
        text: str,
        builtin_speaker: str,
        language: str,
        output_path: Path,
    ) -> SynthesisResult:
        tts, model_load_ms, cache_hit = self._ensure_model(move_to_target=True)

        speaker_start = time.perf_counter()
        available = {speaker.name for speaker in self._builtin_speakers(tts)}
        speaker_discovery_ms = (time.perf_counter() - speaker_start) * 1000
        if builtin_speaker not in available:
            raise ValueError(f"Built-in speaker '{builtin_speaker}' is unavailable")

        synth_start = time.perf_counter()
        tts.tts_to_file(
            text=text,
            speaker=builtin_speaker,
            language=language,
            file_path=str(output_path),
        )
        synth_ms = (time.perf_counter() - synth_start) * 1000

        return SynthesisResult(
            output_path=output_path,
            output_bytes=output_path.stat().st_size,
            builtin_speaker=builtin_speaker,
            language=language,
            model_load_ms=round(model_load_ms, 3),
            speaker_discovery_ms=round(speaker_discovery_ms, 3),
            synth_ms=round(synth_ms, 3),
            wav_write_ms=0.0,
            cache_hit=cache_hit,
        )


def synthesize_with_tempfile(
    engine: TtsEngine,
    *,
    text: str,
    builtin_speaker: str,
    language: str,
) -> SynthesisResult:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        output_path = Path(handle.name)
    return engine.synthesize_to_wav(
        text=text,
        builtin_speaker=builtin_speaker,
        language=language,
        output_path=output_path,
    )
