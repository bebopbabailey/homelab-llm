from __future__ import annotations

from pathlib import Path

from voice_gateway.cli import build_parser


def test_cli_accepts_synth_command(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "synth",
            "--text",
            "hello",
            "--voice",
            "default",
            "--out",
            str(tmp_path / "out.wav"),
        ]
    )
    assert args.command == "synth"
    assert args.voice == "default"
    assert args.play is False


def test_cli_requires_port_for_serve() -> None:
    parser = build_parser()
    args = parser.parse_args(["serve", "--port", "18080"])
    assert args.command == "serve"
    assert args.port == 18080
