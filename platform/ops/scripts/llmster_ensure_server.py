#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from subprocess import CompletedProcess, run


@dataclass(frozen=True)
class LoadSpec:
    model: str
    identifier: str
    context_length: int
    parallel: int
    eval_batch_size: int | None = None
    flash_attention: bool | None = None
    num_experts: int | None = None
    offload_kv_cache_to_gpu: bool | None = None


def parse_load_spec(raw: str) -> LoadSpec:
    parts = raw.split("|")
    if len(parts) not in {4, 8}:
        raise ValueError(f"invalid load spec: {raw!r}")
    model, identifier, context_length, parallel, *rest = parts
    eval_batch_size = None
    flash_attention = None
    num_experts = None
    offload_kv_cache_to_gpu = None
    if rest:
        eval_batch_size_raw, flash_attention_raw, num_experts_raw, offload_kv_raw = rest
        eval_batch_size = int(eval_batch_size_raw) if eval_batch_size_raw.strip() else None
        flash_attention = _parse_optional_bool(flash_attention_raw)
        num_experts = int(num_experts_raw) if num_experts_raw.strip() else None
        offload_kv_cache_to_gpu = _parse_optional_bool(offload_kv_raw)
    return LoadSpec(
        model=model.strip(),
        identifier=identifier.strip(),
        context_length=int(context_length),
        parallel=int(parallel),
        eval_batch_size=eval_batch_size,
        flash_attention=flash_attention,
        num_experts=num_experts,
        offload_kv_cache_to_gpu=offload_kv_cache_to_gpu,
    )


def _parse_optional_bool(raw: str) -> bool | None:
    value = raw.strip().lower()
    if not value:
        return None
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {raw!r}")


def run_checked(cmd: list[str], *, allow_failure: bool = False) -> CompletedProcess[str]:
    proc = run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0 and not allow_failure:
        raise RuntimeError(
            "command failed: {}\nstdout={}\nstderr={}".format(
                " ".join(cmd), proc.stdout.strip(), proc.stderr.strip()
            )
        )
    return proc


def wait_for_models(base_url: str, api_key: str | None, timeout_s: float, poll_s: float) -> dict:
    deadline = time.time() + timeout_s
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    while time.time() < deadline:
        req = urllib.request.Request(f"{base_url}/models", headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=min(10.0, poll_s + 5.0)) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode())
        except urllib.error.HTTPError:
            pass
        except urllib.error.URLError:
            pass
        time.sleep(poll_s)
    raise RuntimeError(f"timed out waiting for {base_url}/models")


def identifier_present(models_body: dict, identifier: str) -> bool:
    data = models_body.get("data", [])
    return any((item or {}).get("id") == identifier for item in data if isinstance(item, dict))


def wait_for_native_models(native_base_url: str, api_key: str | None, timeout_s: float, poll_s: float) -> dict:
    deadline = time.time() + timeout_s
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    while time.time() < deadline:
        req = urllib.request.Request(f"{native_base_url}/models", headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=min(10.0, poll_s + 5.0)) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode())
        except urllib.error.HTTPError:
            pass
        except urllib.error.URLError:
            pass
        time.sleep(poll_s)
    raise RuntimeError(f"timed out waiting for {native_base_url}/models")


def find_loaded_instance(models_body: dict, identifier: str) -> dict | None:
    models = models_body.get("models", [])
    for model in models:
        if not isinstance(model, dict):
            continue
        for instance in model.get("loaded_instances", []) or []:
            if isinstance(instance, dict) and instance.get("id") == identifier:
                return instance
    return None


def load_config_matches(instance: dict | None, spec: LoadSpec) -> bool:
    if not isinstance(instance, dict):
        return False
    config = instance.get("config")
    if not isinstance(config, dict):
        return False
    if config.get("context_length") != spec.context_length:
        return False
    if config.get("parallel") != spec.parallel:
        return False
    expected_pairs = {
        "eval_batch_size": spec.eval_batch_size,
        "flash_attention": spec.flash_attention,
        "num_experts": spec.num_experts,
        "offload_kv_cache_to_gpu": spec.offload_kv_cache_to_gpu,
    }
    for key, expected in expected_pairs.items():
        if expected is not None and config.get(key) != expected:
            return False
    return True


def unload_instance(native_base_url: str, api_key: str | None, identifier: str) -> None:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        f"{native_base_url}/models/unload",
        data=json.dumps({"instance_id": identifier}).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"failed to unload {identifier!r}: status={resp.status}")


def ensure_identifier_loaded(base_url: str, api_key: str | None, identifier: str, timeout_s: float, poll_s: float) -> None:
    deadline = time.time() + timeout_s
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    while time.time() < deadline:
        req = urllib.request.Request(f"{base_url}/models", headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=min(10.0, poll_s + 5.0)) as resp:
                if resp.status != 200:
                    time.sleep(poll_s)
                    continue
                body = json.loads(resp.read().decode())
                if identifier_present(body, identifier):
                    return
        except Exception:
            pass
        time.sleep(poll_s)
    raise RuntimeError(f"timed out waiting for model identifier {identifier!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Thin daemon-aware LM Studio bootstrap for canonical llmster lanes.")
    parser.add_argument("--lms-bin", required=True, help="Pinned versioned lms binary path.")
    parser.add_argument("--bind", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--api-key-env", default="")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--startup-timeout", type=float, default=90.0)
    parser.add_argument(
        "--load-spec",
        action="append",
        default=[],
        help="model|identifier|context_length|parallel",
    )
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    load_specs = [parse_load_spec(spec) for spec in args.load_spec]
    base_url = f"http://{args.bind}:{args.port}/v1"
    native_base_url = f"http://{args.bind}:{args.port}/api/v1"

    run_checked([args.lms_bin, "daemon", "up"])
    run_checked([args.lms_bin, "daemon", "status"])

    # `lms server start` may return non-zero if the server is already running on
    # the target bind/port. The health check below is the actual success gate.
    run_checked(
        [args.lms_bin, "server", "start", "--bind", args.bind, "--port", str(args.port)],
        allow_failure=True,
    )
    models_body = wait_for_models(base_url, api_key, args.startup_timeout, args.poll_interval)
    native_models_body = wait_for_native_models(native_base_url, api_key, args.startup_timeout, args.poll_interval)

    for spec in load_specs:
        if identifier_present(models_body, spec.identifier):
            instance = find_loaded_instance(native_models_body, spec.identifier)
            if load_config_matches(instance, spec):
                continue
            unload_instance(native_base_url, api_key, spec.identifier)
            models_body = wait_for_models(base_url, api_key, args.startup_timeout, args.poll_interval)
            native_models_body = wait_for_native_models(native_base_url, api_key, args.startup_timeout, args.poll_interval)
        run_checked(
            [
                args.lms_bin,
                "load",
                spec.model,
                "--identifier",
                spec.identifier,
                "--context-length",
                str(spec.context_length),
                "--parallel",
                str(spec.parallel),
                "-y",
            ]
        )
        ensure_identifier_loaded(base_url, api_key, spec.identifier, args.startup_timeout, args.poll_interval)
        models_body = wait_for_models(base_url, api_key, args.startup_timeout, args.poll_interval)
        native_models_body = wait_for_native_models(native_base_url, api_key, args.startup_timeout, args.poll_interval)
        if not load_config_matches(find_loaded_instance(native_models_body, spec.identifier), spec):
            raise RuntimeError(f"loaded config drift for {spec.identifier!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
