from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from voice_gateway.api import create_app
from voice_gateway.audio_out import PlaybackError, play_wav
from voice_gateway.logging import emit_log
from voice_gateway.service import main as service_main
from voice_gateway.settings import Settings
from voice_gateway.tts_engine import DependencyBlockedError, TtsEngine, XttsEngine
from voice_gateway.voice_config import VoiceConfigError, load_voice_config, resolve_voice


def _engine_from_settings(settings: Settings) -> TtsEngine:
    return XttsEngine(model_name=settings.tts_model, device=settings.tts_device)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Voice Gateway Phase 1 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-speakers", help="List discovered built-in XTTS speakers")

    synth_parser = subparsers.add_parser("synth", help="Synthesize WAV output from text")
    synth_parser.add_argument("--text", required=True)
    synth_parser.add_argument("--voice", default="default")
    synth_parser.add_argument("--language", default=None)
    synth_parser.add_argument("--out", required=True)
    synth_parser.add_argument("--play", action="store_true")

    serve_parser = subparsers.add_parser("serve", help="Run the localhost HTTP wrapper")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", required=True, type=int)

    return parser


def _list_speakers(settings: Settings, engine: TtsEngine) -> int:
    discovered = sorted(speaker.name for speaker in engine.discover_builtin_speakers())
    config = load_voice_config(settings.voice_config_path)
    default_voice, default_builtin = resolve_voice(
        requested_voice="default",
        config=config,
        discovered_builtin_speakers=discovered,
    )
    payload = {
        "default_voice": default_voice,
        "resolved_builtin_speaker": default_builtin,
        "discovered_builtin_speakers": discovered,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _synth(settings: Settings, engine: TtsEngine, args: argparse.Namespace) -> int:
    total_start = time.perf_counter()
    discovered = sorted(speaker.name for speaker in engine.discover_builtin_speakers())
    config = load_voice_config(settings.voice_config_path)
    speaker_id, builtin_speaker = resolve_voice(
        requested_voice=args.voice,
        config=config,
        discovered_builtin_speakers=discovered,
    )
    output_path = Path(args.out)
    result = engine.synthesize_to_wav(
        text=args.text,
        builtin_speaker=builtin_speaker,
        language=args.language or settings.default_language,
        output_path=output_path,
    )
    playback_ms = 0.0
    if args.play:
        playback_ms = play_wav(output_path)
    total_ms = (time.perf_counter() - total_start) * 1000
    emit_log(
        event="synth",
        log_path=settings.log_path,
        request_id="cli",
        source="cli",
        route="voice-gateway synth",
        model=settings.tts_model,
        speaker_id=speaker_id,
        resolved_builtin_speaker=builtin_speaker,
        language=args.language or settings.default_language,
        input_chars=len(args.text),
        speaker_discovery_ms=result.speaker_discovery_ms,
        model_load_ms=result.model_load_ms,
        synth_ms=result.synth_ms,
        wav_write_ms=result.wav_write_ms,
        playback_ms=round(playback_ms, 3),
        total_ms=round(total_ms, 3),
        output_bytes=result.output_bytes,
        status="ok",
        error_code=None,
        exception_class=None,
    )
    print(str(output_path))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "serve":
        sys.argv = [sys.argv[0], "--host", args.host, "--port", str(args.port)]
        return service_main()

    settings = Settings()
    engine = _engine_from_settings(settings)
    try:
        if args.command == "list-speakers":
            return _list_speakers(settings, engine)
        if args.command == "synth":
            return _synth(settings, engine, args)
    except (DependencyBlockedError, VoiceConfigError, PlaybackError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
