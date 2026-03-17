from __future__ import annotations

import argparse

import uvicorn

from voice_gateway.api import create_app
from voice_gateway.settings import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Voice Gateway HTTP service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", required=True, type=int)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings(gateway_host=args.host, gateway_port=args.port)
    uvicorn.run(create_app(settings=settings), host=settings.gateway_host, port=settings.gateway_port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
