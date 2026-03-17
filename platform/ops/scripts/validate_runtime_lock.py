#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = REPO_ROOT / "platform/ops/runtime-lock.json"
STUDIO_WRAPPER = REPO_ROOT / "platform/ops/scripts/studio_run_utility.sh"

PATCH_PATHS = [
    REPO_ROOT / "layer-gateway/optillm-proxy/scripts/apply_optillm_patches.sh",
    REPO_ROOT / "layer-gateway/optillm-proxy/patches/optillm.patch",
]
DOC_PATHS = [
    REPO_ROOT / "docs/foundation/runtime-lock.md",
    REPO_ROOT / "docs/_core/SOURCES_OF_TRUTH.md",
    REPO_ROOT / "docs/_core/CHANGE_RULES.md",
    REPO_ROOT / "docs/foundation/testing.md",
    REPO_ROOT / "layer-gateway/optillm-proxy/SERVICE_SPEC.md",
    REPO_ROOT / "layer-gateway/optillm-proxy/RUNBOOK.md",
    REPO_ROOT / "layer-gateway/optillm-proxy/AGENTS.md",
    REPO_ROOT / "layer-gateway/litellm-orch/SERVICE_SPEC.md",
    REPO_ROOT / "layer-gateway/litellm-orch/RUNBOOK.md",
    REPO_ROOT / "docs/foundation/mlx-registry.md",
    REPO_ROOT / "docs/PLATFORM_DOSSIER.md",
    REPO_ROOT / "docs/INTEGRATIONS.md",
]


def run(cmd, cwd=None, check=True):
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def studio_run(command, host):
    proc = run([str(STUDIO_WRAPPER), "--host", host, "--", command], check=False)
    return proc


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def load_lock(path=LOCK_PATH):
    return json.loads(read_text(path))


def gitlink_sha(path):
    proc = run(["git", "submodule", "status", path], cwd=REPO_ROOT)
    text = proc.stdout.strip()
    parts = text.split()
    if not parts:
        raise RuntimeError(f"unable to parse submodule status for {path}")
    return parts[0].lstrip("+-U")


def file_contains(path, pattern):
    return pattern in read_text(path)


def router_assertions(router_text):
    ok_drop = re.search(r"^\s*drop_params:\s*true\s*$", router_text, re.M) is not None
    ok_fast_main = re.search(r'\{\s*"fast"\s*:\s*\[\s*"main"\s*\]\s*\}', router_text) is not None
    return ok_drop, ok_fast_main


def lane_override_assertions(argv, override):
    failures = []
    if not override:
        return failures
    if override.get("tool_choice_mode") == "auto" and "--enable-auto-tool-choice" not in argv:
        failures.append("missing --enable-auto-tool-choice")
    parser = override.get("tool_call_parser", "__missing__")
    if parser != "__missing__":
        if "--tool-call-parser" not in argv or parser not in argv:
            failures.append(f"missing --tool-call-parser {parser}")
    reasoning = override.get("reasoning_parser", "__missing__")
    if reasoning is None:
        if "--reasoning-parser" in argv:
            failures.append("unexpected --reasoning-parser")
    elif reasoning != "__missing__":
        if "--reasoning-parser" not in argv or reasoning not in argv:
            failures.append(f"missing --reasoning-parser {reasoning}")
    return failures


def parse_systemd_execstart(text):
    match = re.search(r"ExecStart=.*? --host (\S+) --port (\d+)", text)
    if not match:
        return None, None
    return match.group(1), int(match.group(2))


def check_fast(lock):
    failures = []
    if not LOCK_PATH.exists():
        failures.append("missing platform/ops/runtime-lock.json")
        return failures

    for path, sha in lock["submodules"].items():
        current = gitlink_sha(path)
        if current != sha:
            failures.append(f"submodule mismatch {path}: {current} != {sha}")

    pyproject = read_text(REPO_ROOT / "layer-gateway/optillm-proxy/pyproject.toml")
    if 'optillm==0.3.12' not in pyproject:
        failures.append("optillm pin missing from pyproject.toml")

    uv_lock = read_text(REPO_ROOT / "layer-gateway/optillm-proxy/uv.lock")
    if "algorithmicsuperintelligence/optillm" in uv_lock or "git+https://github.com/algorithmicsuperintelligence/optillm" in uv_lock:
        failures.append("uv.lock still contains git-sourced optillm")

    for patch_path in PATCH_PATHS:
        if patch_path.exists():
            failures.append(f"patch artifact present: {patch_path.relative_to(REPO_ROOT)}")

    deploy = read_text(REPO_ROOT / "layer-gateway/optillm-proxy/scripts/deploy_studio.sh")
    if "git pull --ff-only" in deploy:
        failures.append("deploy_studio.sh still uses git pull --ff-only")
    if "apply_optillm_patches" in deploy:
        failures.append("deploy_studio.sh still references apply_optillm_patches")
    if "git checkout --detach" not in deploy or "uv sync --frozen" not in deploy:
        failures.append("deploy_studio.sh missing exact-SHA deploy markers")

    router_text = read_text(REPO_ROOT / lock["litellm"]["router_yaml"])
    ok_drop, ok_fast_main = router_assertions(router_text)
    if not ok_drop:
        failures.append("router.yaml missing drop_params: true")
    if not ok_fast_main:
        failures.append("router.yaml missing fast -> main fallback")

    for doc in DOC_PATHS:
        if not doc.exists():
            failures.append(f"missing canon doc: {doc.relative_to(REPO_ROOT)}")

    return failures


def parse_remote_json(proc, context):
    if proc.returncode != 0:
        raise RuntimeError(f"remote command failed ({context}): {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def check_full(lock, host):
    failures = check_fast(lock)

    target_sha = lock["submodules"]["layer-gateway/optillm-proxy"]
    proc = studio_run("cd /Users/thestudio/optillm-proxy && git rev-parse HEAD", host)
    if proc.returncode != 0 or proc.stdout.strip() != target_sha:
        failures.append("studio optillm-proxy HEAD does not match runtime lock")

    proc = studio_run("/Users/thestudio/optillm-proxy/.venv/bin/python - <<'PY'\nimport importlib.metadata as md, json\nd = md.distribution('optillm')\nprint(json.dumps({'version': md.version('optillm'), 'has_direct_url': any(str(f).endswith('direct_url.json') for f in (d.files or []))}))\nPY", host)
    try:
        pkg = parse_remote_json(proc, "studio optillm package")
        if pkg.get("version") != lock["optillm_proxy"]["package"]["version"]:
            failures.append("studio optillm version mismatch")
        if pkg.get("has_direct_url"):
            failures.append("studio optillm install still has direct_url provenance")
    except Exception as exc:
        failures.append(str(exc))

    label = lock["optillm_proxy"]["deploy"]["label"]
    proc = studio_run(f"sudo launchctl print system/{label}", host)
    if proc.returncode != 0 or "state = running" not in proc.stdout:
        failures.append("studio optillm launchd label not running")

    proc = studio_run(f"sudo plutil -convert json -o - /Library/LaunchDaemons/{label}.plist", host)
    try:
        plist = parse_remote_json(proc, f"plist {label}")
        argv = plist.get("ProgramArguments", [])
        runtime = lock["optillm_proxy"]["runtime"]
        try:
            host_index = argv.index("--host")
            observed_host = argv[host_index + 1]
        except Exception:
            observed_host = None
        try:
            port_index = argv.index("--port")
            observed_port = int(argv[port_index + 1])
        except Exception:
            observed_port = None
        try:
            base_index = argv.index("--base-url")
            observed_base = argv[base_index + 1]
        except Exception:
            observed_base = None
        try:
            model_index = argv.index("--model")
            observed_model = argv[model_index + 1]
        except Exception:
            observed_model = None
        if observed_host != runtime["bind_host"]:
            failures.append("studio optillm bind host drift")
        if observed_port != runtime["port"]:
            failures.append("studio optillm port drift")
        if observed_base != runtime["base_url"]:
            failures.append("studio optillm base-url drift")
        if observed_model != runtime["model"]:
            failures.append("studio optillm model drift")
    except Exception as exc:
        failures.append(str(exc))

    for port, label in lock["mlx"]["lanes"].items():
        proc = studio_run(f"sudo plutil -convert json -o - /Library/LaunchDaemons/{label}.plist", host)
        try:
            plist = parse_remote_json(proc, f"plist {label}")
            env = plist.get("EnvironmentVariables", {})
            argv = plist.get("ProgramArguments", [])
            try:
                host_index = argv.index("--host")
                observed_host = argv[host_index + 1]
            except Exception:
                observed_host = None
            if observed_host != lock["mlx"].get("bind_host"):
                failures.append(f"{label} bind host drift")
            if env.get("VLLM_METAL_MEMORY_FRACTION") != lock["mlx"]["memory_fraction"]:
                failures.append(f"{label} memory fraction drift")
            if "--no-async-scheduling" not in argv:
                failures.append(f"{label} missing --no-async-scheduling")
            if any("paged" in str(arg).lower() for arg in argv) or env.get("VLLM_METAL_USE_PAGED_ATTENTION"):
                failures.append(f"{label} enables paged attention")
            override = (lock.get("mlx", {}).get("lane_overrides") or {}).get(str(port))
            for failure in lane_override_assertions(argv, override):
                failures.append(f"{label} {failure}")
        except Exception as exc:
            failures.append(str(exc))

    proc = run(["systemctl", "is-active", "litellm-orch.service"], check=False)
    if proc.returncode != 0 or proc.stdout.strip() != "active":
        failures.append("litellm-orch.service is not active")

    proc = run(["systemctl", "show", "litellm-orch.service", "-p", "ExecStart"], check=False)
    host_value, port_value = parse_systemd_execstart(proc.stdout)
    if host_value != lock["litellm"]["bind_host"]:
        failures.append("litellm-orch bind host drift")
    if port_value != lock["litellm"]["port"]:
        failures.append("litellm-orch port drift")

    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["fast", "full"], required=True)
    parser.add_argument("--host", default="studio")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    lock = load_lock()
    failures = check_fast(lock) if args.mode == "fast" else check_full(lock, args.host)
    result = {"mode": args.mode, "ok": not failures, "failures": failures}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if failures:
            print("Runtime lock validation failed:")
            for failure in failures:
                print(f"- {failure}")
        else:
            print("Runtime lock validation passed")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
