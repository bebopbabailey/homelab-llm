from __future__ import annotations

import argparse
import json
import os
import sys
from urllib import error, parse, request

from voice_gateway.ops_registry import OpsRegistryError, find_curated_model, load_curated_tts_registry
from voice_gateway.settings import Settings


def _headers(*, api_key: str | None, with_json: bool = False) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if with_json:
        headers["Content-Type"] = "application/json"
    return headers


def _request_json(
    *,
    base_url: str,
    path: str,
    method: str = "GET",
    api_key: str | None = None,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}{path}",
        method=method,
        data=body,
        headers=_headers(api_key=api_key, with_json=payload is not None),
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"request failed ({exc.code}) {path}: {message}") from exc
    except error.URLError as exc:
        raise SystemExit(f"request failed {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"unexpected response from {path}: expected object")
    return data


def _base_url_from_args(args: argparse.Namespace) -> str:
    return args.base_url or os.environ.get("VOICE_GATEWAY_BASE_URL") or "http://192.168.1.93:18080"


def _api_key_from_args(args: argparse.Namespace) -> str | None:
    return args.api_key or os.environ.get("VOICE_GATEWAY_API_KEY")


def _resolve_curated_selector(*, settings: Settings, selector: str) -> str:
    models = load_curated_tts_registry(settings.tts_registry_path)
    selected = find_curated_model(models=models, selector=selector)
    return selected.model_id


def _cmd_registry_list(settings: Settings) -> int:
    models = load_curated_tts_registry(settings.tts_registry_path)
    print(json.dumps({"path": str(settings.tts_registry_path), "models": [m.to_dict() for m in models]}, indent=2))
    return 0


def _cmd_status(settings: Settings, args: argparse.Namespace) -> int:
    base_url = _base_url_from_args(args)
    api_key = _api_key_from_args(args)
    state = _request_json(base_url=base_url, path="/ops/api/state", api_key=api_key)
    print(json.dumps(state, indent=2))
    return 0


def _cmd_mutation(settings: Settings, args: argparse.Namespace, *, route: str) -> int:
    selector = args.model
    model_id = _resolve_curated_selector(settings=settings, selector=selector)
    base_url = _base_url_from_args(args)
    api_key = _api_key_from_args(args)
    response = _request_json(
        base_url=base_url,
        path=route,
        method="POST",
        api_key=api_key,
        payload={"model_id": model_id},
    )
    print(json.dumps({"selector": selector, "model_id": model_id, "response": response}, indent=2))
    return 0


def _cmd_promotion_plan(settings: Settings, args: argparse.Namespace) -> int:
    selector = args.model
    model_id = _resolve_curated_selector(settings=settings, selector=selector)
    base_url = _base_url_from_args(args)
    api_key = _api_key_from_args(args)
    voice_ids = [value.strip() for value in args.voice_ids.split(",") if value.strip()]
    payload = {
        "backend_tts_model": model_id,
        "fallback_voice_id": args.fallback_voice_id,
        "unknown_voice_policy": args.unknown_voice_policy,
        "include_default_alloy_aliases": True,
        "voice_ids": voice_ids,
    }
    response = _request_json(
        base_url=base_url,
        path="/ops/api/promotion/plan",
        method="POST",
        api_key=api_key,
        payload=payload,
    )
    commands = response.get("commands")
    if isinstance(commands, str):
        print(commands)
    else:
        print(json.dumps(response, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Voice Gateway curated TTS control plane")
    parser.add_argument("--base-url", default=None, help="voice-gateway base URL (default from env or Orin LAN)")
    parser.add_argument("--api-key", default=None, help="voice-gateway bearer token")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("registry-list", help="print curated repo registry")
    subparsers.add_parser("status", help="show live ops state")

    for name in ("download", "load", "unload"):
        p = subparsers.add_parser(name, help=f"{name} a curated model by id or model_id")
        p.add_argument("model", help="curated id or exact model_id")

    plan = subparsers.add_parser("promotion-plan", help="generate manual promotion commands")
    plan.add_argument("model", help="curated id or exact model_id")
    plan.add_argument("--voice-ids", default="", help="comma-separated backend voice ids")
    plan.add_argument("--fallback-voice-id", default="default")
    plan.add_argument("--unknown-voice-policy", default="reject", choices=["reject", "fallback"])
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings()
    try:
        if args.command == "registry-list":
            return _cmd_registry_list(settings)
        if args.command == "status":
            return _cmd_status(settings, args)
        if args.command == "download":
            return _cmd_mutation(settings, args, route="/ops/api/models/download")
        if args.command == "load":
            return _cmd_mutation(settings, args, route="/ops/api/models/load")
        if args.command == "unload":
            return _cmd_mutation(settings, args, route="/ops/api/models/unload")
        if args.command == "promotion-plan":
            return _cmd_promotion_plan(settings, args)
    except OpsRegistryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
