#!/usr/bin/env python3
"""Run end-to-end viability gates for the experimental OptiLLM-on-MLX patch.

This orchestrates smoke + benchmark checks and computes a final decision:
- GO
- CONDITIONAL_GO
- NO_GO
- UNVERIFIED
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


DECISION_GO = "GO"
DECISION_CONDITIONAL_GO = "CONDITIONAL_GO"
DECISION_NO_GO = "NO_GO"
DECISION_UNVERIFIED = "UNVERIFIED"

DEFAULT_URL = "http://127.0.0.1:8130/v1/chat/completions"
DEFAULT_MODELS = "main,gpt-oss-20b,gpt-oss-120b"
DEFAULT_REQUIRED_MODELS = "main,gpt-oss-20b"
DEFAULT_CONCURRENCY_VALUES = "1,4,8"
DEFAULT_REPEATS = 3
DEFAULT_MAX_TOKENS = 256
DEFAULT_SMOKE_TIMEOUT = 180
DEFAULT_BENCH_TIMEOUT = 240
DEFAULT_OUTPUT_DIR = "/tmp"
DEFAULT_P50_OVERHEAD_PCT = 25.0
DEFAULT_P95_OVERHEAD_PCT = 35.0
DEFAULT_ERROR_DELTA_PCT = 1.0
DEFAULT_ENTROPY_METADATA_RATE_MIN = 0.95
DEFAULT_MIN_THROUGHPUT_DELTA_PCT = -15.0
DEFAULT_MAX_ERROR_RATE_PCT = 0.5


@dataclass(frozen=True)
class Thresholds:
    p50_overhead_pct: float
    p95_overhead_pct: float
    error_delta_pct: float
    entropy_metadata_rate_min: float
    min_throughput_delta_pct: float
    max_error_rate_pct: float


def parse_csv(text: str) -> List[str]:
    return [token.strip() for token in text.split(",") if token.strip()]


def parse_csv_int(text: str) -> List[int]:
    values: List[int] = []
    for token in parse_csv(text):
        values.append(int(token))
    return values


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _to_csv(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    raise ValueError(f"expected string or list for csv-like field, got: {type(value).__name__}")


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"expected boolean-like value, got: {value!r}")


def _normalize_output_path(path_value: str | None, base_dir: Path | None) -> str | None:
    if not path_value:
        return None
    candidate = Path(path_value)
    if candidate.is_absolute() or base_dir is None:
        return str(candidate)
    return str((base_dir / candidate).resolve())


def _load_json_file(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} did not parse to an object")
    return payload


def _resolve_gate_profile(gate_config_path: str | None) -> tuple[Dict[str, Any], Path | None]:
    if not gate_config_path:
        return {}, None

    path = Path(gate_config_path).resolve()
    raw = _load_json_file(path)
    profile = raw.get("viability_gate") if isinstance(raw.get("viability_gate"), dict) else raw
    if not isinstance(profile, dict):
        raise ValueError("gate config must be an object or contain a 'viability_gate' object")
    return profile, path.parent


def _profile_value(profile: Dict[str, Any], *keys: str) -> Any:
    current: Any = profile
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def pct_delta(base: float, value: float) -> float:
    if base <= 0:
        return 0.0 if value <= 0 else 100.0
    return ((value - base) / base) * 100.0


def error_rate_pct(mode_summary: Dict[str, Any]) -> float:
    requests = float(mode_summary.get("requests", 0) or 0)
    failure = float(mode_summary.get("failure", 0) or 0)
    if requests <= 0:
        return 0.0
    return (failure / requests) * 100.0


def run_cmd(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def run_smoke(
    *,
    scripts_dir: Path,
    url: str,
    model: str,
    max_tokens: int,
    timeout: int,
    bearer: str | None,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(scripts_dir / "smoke_decode.py"),
        "--url",
        url,
        "--model",
        model,
        "--max-tokens",
        str(max_tokens),
        "--timeout",
        str(timeout),
        "--expect-metadata",
    ]
    if bearer:
        cmd += ["--bearer", bearer]

    completed = run_cmd(cmd)

    payload: Dict[str, Any] = {}
    stdout = completed.stdout.strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = {"raw_stdout": stdout}

    rows = payload.get("results") if isinstance(payload, dict) else None
    default_ok = False
    entropy_ok = False
    behavior_changed = False
    functional_status = "unverified"

    if isinstance(rows, list) and len(rows) >= 2:
        by_mode = {row.get("mode"): row for row in rows if isinstance(row, dict)}
        default_row = by_mode.get("default", {})
        entropy_row = by_mode.get("entropy", {})

        default_ok = (
            default_row.get("status") == 200
            and not bool(default_row.get("has_decoding_metadata"))
        )
        entropy_ok = (
            entropy_row.get("status") == 200
            and bool(entropy_row.get("has_decoding_metadata"))
        )
        behavior_changed = (
            str(default_row.get("text_preview", ""))
            != str(entropy_row.get("text_preview", ""))
        )
        default_status = default_row.get("status")
        entropy_status = entropy_row.get("status")
        reachable = default_status == 200 or entropy_status == 200

        if default_ok and entropy_ok:
            functional_status = "pass"
        elif reachable:
            functional_status = "fail"
        else:
            functional_status = "unverified"

    return {
        "model": model,
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
        "default_ok": default_ok,
        "entropy_ok": entropy_ok,
        "behavior_changed": behavior_changed,
        "functional_pass": default_ok and entropy_ok,
        "functional_status": functional_status,
    }


def run_bench(
    *,
    scripts_dir: Path,
    url: str,
    model: str,
    prompts: str | None,
    repeats: int,
    max_tokens: int,
    timeout: int,
    concurrency: int,
    bearer: str | None,
    work_dir: Path,
) -> Dict[str, Any]:
    output_path = work_dir / f"bench_{model.replace('/', '_')}_c{concurrency}.json"
    cmd = [
        sys.executable,
        str(scripts_dir / "bench_decode.py"),
        "--url",
        url,
        "--model",
        model,
        "--repeats",
        str(repeats),
        "--max-tokens",
        str(max_tokens),
        "--timeout",
        str(timeout),
        "--concurrency",
        str(concurrency),
        "--json-out",
        str(output_path),
    ]
    if prompts:
        cmd += ["--prompts", prompts]
    if bearer:
        cmd += ["--bearer", bearer]

    completed = run_cmd(cmd)

    summary: Dict[str, Any] = {}
    if output_path.exists():
        try:
            summary = json.loads(output_path.read_text())
        except json.JSONDecodeError:
            summary = {}

    return {
        "model": model,
        "concurrency": concurrency,
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "summary": summary,
        "summary_path": str(output_path),
    }


def evaluate_bench_result(bench: Dict[str, Any], thresholds: Thresholds) -> Dict[str, Any]:
    summary = bench.get("summary") or {}
    modes = summary.get("modes") if isinstance(summary, dict) else {}
    default_mode = (modes or {}).get("default") if isinstance(modes, dict) else None
    entropy_mode = (modes or {}).get("entropy") if isinstance(modes, dict) else None

    if not isinstance(default_mode, dict) or not isinstance(entropy_mode, dict):
        return {
            "evaluated": False,
            "status": "unverified",
            "reason": "missing default/entropy summaries",
        }

    default_latency = default_mode.get("latency_seconds", {})
    entropy_latency = entropy_mode.get("latency_seconds", {})

    default_success = int(default_mode.get("success", 0) or 0)
    entropy_success = int(entropy_mode.get("success", 0) or 0)
    if default_success <= 0 or entropy_success <= 0:
        return {
            "evaluated": False,
            "status": "unverified",
            "reason": "no successful baseline or entropy responses",
        }

    p50_base = float(default_latency.get("p50", 0) or 0)
    p95_base = float(default_latency.get("p95", 0) or 0)
    p50_entropy = float(entropy_latency.get("p50", 0) or 0)
    p95_entropy = float(entropy_latency.get("p95", 0) or 0)

    p50_overhead = pct_delta(p50_base, p50_entropy)
    p95_overhead = pct_delta(p95_base, p95_entropy)

    err_default = error_rate_pct(default_mode)
    err_entropy = error_rate_pct(entropy_mode)
    err_delta = err_entropy - err_default

    metadata_rate = float(entropy_mode.get("metadata_rate", 0.0) or 0.0)
    default_tps = float(default_mode.get("completion_tokens_per_second", 0.0) or 0.0)
    entropy_tps = float(entropy_mode.get("completion_tokens_per_second", 0.0) or 0.0)
    throughput_delta = pct_delta(default_tps, entropy_tps)

    pass_perf = (
        p50_overhead <= thresholds.p50_overhead_pct
        and p95_overhead <= thresholds.p95_overhead_pct
        and err_delta <= thresholds.error_delta_pct
        and err_entropy <= thresholds.max_error_rate_pct
        and err_default <= thresholds.max_error_rate_pct
        and throughput_delta >= thresholds.min_throughput_delta_pct
        and metadata_rate >= thresholds.entropy_metadata_rate_min
    )

    return {
        "evaluated": True,
        "status": "pass" if pass_perf else "fail",
        "p50_overhead_pct": round(p50_overhead, 3),
        "p95_overhead_pct": round(p95_overhead, 3),
        "error_rate_default_pct": round(err_default, 3),
        "error_rate_entropy_pct": round(err_entropy, 3),
        "error_delta_pct": round(err_delta, 3),
        "throughput_default_toks_per_s": round(default_tps, 4),
        "throughput_entropy_toks_per_s": round(entropy_tps, 4),
        "throughput_delta_pct": round(throughput_delta, 3),
        "entropy_metadata_rate": round(metadata_rate, 4),
    }


def aggregate_model_status(
    smoke: Dict[str, Any] | None,
    bench_evals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if smoke is None:
        return {"status": "unverified", "reason": "smoke not executed"}

    functional_status = str(smoke.get("functional_status", "unverified"))
    if functional_status == "unverified":
        return {"status": "unverified", "reason": "functional smoke unverified"}

    if functional_status == "fail":
        return {"status": "fail", "reason": "functional smoke failed"}

    if not bench_evals:
        return {"status": "unverified", "reason": "no benchmark evaluations"}

    statuses = [e.get("status") for e in bench_evals]

    if any(status == "fail" for status in statuses):
        return {"status": "fail", "reason": "one or more benchmark gates failed"}

    if any(status not in {"pass"} for status in statuses):
        return {"status": "unverified", "reason": "benchmark data incomplete"}

    return {
        "status": "pass",
        "reason": "functional + performance gates passed",
        "behavior_changed": bool(smoke.get("behavior_changed", False)),
    }


def decide_final_status(
    *,
    model_statuses: Dict[str, str],
    required_models: Iterable[str],
) -> tuple[str, List[str]]:
    required = [m for m in required_models if m in model_statuses]
    optional = [m for m in model_statuses if m not in required]

    reasons: List[str] = []

    for model in required:
        if model_statuses[model] == "fail":
            reasons.append(f"required model '{model}' failed")
            return DECISION_NO_GO, reasons

    for model in required:
        if model_statuses[model] == "unverified":
            reasons.append(f"required model '{model}' unverified")
            return DECISION_UNVERIFIED, reasons

    optional_problem = [m for m in optional if model_statuses[m] in {"fail", "unverified"}]
    if optional_problem:
        reasons.append("optional model gates incomplete: " + ", ".join(optional_problem))
        return DECISION_CONDITIONAL_GO, reasons

    reasons.append("all required and optional model gates passed")
    return DECISION_GO, reasons


def maybe_check_patch_rebase(patch_path: Path) -> Dict[str, Any]:
    """Optional maintainability check: can the patch still apply to upstream."""
    if not patch_path.exists():
        return {
            "status": "unverified",
            "reason": f"patch file not found: {patch_path}",
        }

    workspace = Path(tempfile.mkdtemp(prefix="optillm_mlx_rebase_check_"))
    repo = workspace / "mlx-lm"

    clone = run_cmd(["git", "clone", "--depth", "1", "https://github.com/ml-explore/mlx-lm.git", str(repo)])
    if clone.returncode != 0:
        return {
            "status": "unverified",
            "reason": "failed to clone upstream mlx-lm",
            "stdout": clone.stdout,
            "stderr": clone.stderr,
        }

    check = run_cmd(["git", "-C", str(repo), "apply", "--check", str(patch_path)])
    if check.returncode == 0:
        return {"status": "pass", "reason": "server.diff applies cleanly to upstream"}

    return {
        "status": "fail",
        "reason": "server.diff does not apply cleanly to upstream",
        "stdout": check.stdout,
        "stderr": check.stderr,
    }


def evaluate_quality_gate(report: Dict[str, Any] | None, required: bool) -> Dict[str, Any]:
    if report is None:
        return {
            "status": "unverified" if required else "skipped",
            "reason": "quality report not provided",
        }

    status = report.get("status")
    if status is None and isinstance(report.get("passed"), bool):
        status = "pass" if report["passed"] else "fail"

    if status not in {"pass", "fail", "unverified"}:
        return {
            "status": "unverified",
            "reason": "quality report missing valid status",
            "raw_status": status,
        }

    reason = report.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        if status == "pass":
            reason = "quality report passed"
        elif status == "fail":
            reason = "quality report failed"
        else:
            reason = "quality report unverified"

    payload: Dict[str, Any] = {
        "status": status,
        "reason": reason,
    }
    metrics = report.get("metrics")
    if isinstance(metrics, dict):
        payload["metrics"] = metrics
    return payload


def _resolve_effective_inputs(args: argparse.Namespace, profile: Dict[str, Any], profile_base: Path | None) -> Dict[str, Any]:
    thresholds_cfg = _profile_value(profile, "thresholds") or {}
    if thresholds_cfg and not isinstance(thresholds_cfg, dict):
        raise ValueError("thresholds in gate config must be an object")

    quality_cfg = _profile_value(profile, "quality") or {}
    if quality_cfg and not isinstance(quality_cfg, dict):
        raise ValueError("quality in gate config must be an object")

    models_csv = _to_csv(_first_not_none(args.models, _profile_value(profile, "models"), DEFAULT_MODELS))
    required_models_csv = _to_csv(
        _first_not_none(args.required_models, _profile_value(profile, "required_models"), DEFAULT_REQUIRED_MODELS)
    )
    concurrency_csv = _to_csv(
        _first_not_none(args.concurrency_values, _profile_value(profile, "concurrency_values"), DEFAULT_CONCURRENCY_VALUES)
    )

    prompts = _first_not_none(args.prompts, _profile_value(profile, "prompts"))
    if isinstance(prompts, str):
        prompts = _normalize_output_path(prompts, profile_base)

    repeats = int(_first_not_none(args.repeats, _profile_value(profile, "repeats"), DEFAULT_REPEATS))
    max_tokens = int(_first_not_none(args.max_tokens, _profile_value(profile, "max_tokens"), DEFAULT_MAX_TOKENS))
    smoke_timeout = int(
        _first_not_none(args.smoke_timeout, _profile_value(profile, "smoke_timeout"), DEFAULT_SMOKE_TIMEOUT)
    )
    bench_timeout = int(
        _first_not_none(args.bench_timeout, _profile_value(profile, "bench_timeout"), DEFAULT_BENCH_TIMEOUT)
    )

    output_dir = _first_not_none(args.output_dir, _profile_value(profile, "output_dir"), DEFAULT_OUTPUT_DIR)
    output_dir = _normalize_output_path(str(output_dir), profile_base) or DEFAULT_OUTPUT_DIR

    p50_overhead_pct = float(
        _first_not_none(
            args.p50_overhead_pct,
            _profile_value(thresholds_cfg, "p50_overhead_pct"),
            DEFAULT_P50_OVERHEAD_PCT,
        )
    )
    p95_overhead_pct = float(
        _first_not_none(
            args.p95_overhead_pct,
            _profile_value(thresholds_cfg, "p95_overhead_pct"),
            DEFAULT_P95_OVERHEAD_PCT,
        )
    )
    error_delta_pct = float(
        _first_not_none(
            args.error_delta_pct,
            _profile_value(thresholds_cfg, "error_delta_pct"),
            DEFAULT_ERROR_DELTA_PCT,
        )
    )
    entropy_metadata_rate_min = float(
        _first_not_none(
            args.entropy_metadata_rate_min,
            _profile_value(thresholds_cfg, "entropy_metadata_rate_min"),
            DEFAULT_ENTROPY_METADATA_RATE_MIN,
        )
    )
    min_throughput_delta_pct = float(
        _first_not_none(
            args.min_throughput_delta_pct,
            _profile_value(thresholds_cfg, "min_throughput_delta_pct"),
            DEFAULT_MIN_THROUGHPUT_DELTA_PCT,
        )
    )
    max_error_rate_pct = float(
        _first_not_none(
            args.max_error_rate_pct,
            _profile_value(thresholds_cfg, "max_error_rate_pct"),
            DEFAULT_MAX_ERROR_RATE_PCT,
        )
    )

    cfg_check_patch = _first_not_none(
        _profile_value(profile, "check_upstream_patch"),
        _profile_value(profile, "maintainability", "check_upstream_patch"),
    )
    check_upstream_patch = bool(args.check_upstream_patch)
    if not check_upstream_patch and cfg_check_patch is not None:
        check_upstream_patch = _to_bool(cfg_check_patch)

    patch_path = _first_not_none(args.patch_path, _profile_value(profile, "patch_path"))
    patch_path = _normalize_output_path(str(patch_path), profile_base) if patch_path else None

    quality_required = bool(args.quality_required)
    if not quality_required and _profile_value(quality_cfg, "required") is not None:
        quality_required = _to_bool(_profile_value(quality_cfg, "required"))

    quality_report = _first_not_none(args.quality_report, _profile_value(quality_cfg, "report_path"))
    quality_report = _normalize_output_path(str(quality_report), profile_base) if quality_report else None

    return {
        "url": _first_not_none(args.url, _profile_value(profile, "url"), DEFAULT_URL),
        "models": parse_csv(models_csv or DEFAULT_MODELS),
        "required_models": parse_csv(required_models_csv or DEFAULT_REQUIRED_MODELS),
        "concurrency_values": parse_csv_int(concurrency_csv or DEFAULT_CONCURRENCY_VALUES),
        "prompts": prompts,
        "repeats": repeats,
        "max_tokens": max_tokens,
        "smoke_timeout": smoke_timeout,
        "bench_timeout": bench_timeout,
        "bearer": _first_not_none(args.bearer, _profile_value(profile, "bearer")),
        "output_dir": output_dir,
        "check_upstream_patch": check_upstream_patch,
        "patch_path": patch_path,
        "quality_required": quality_required,
        "quality_report": quality_report,
        "thresholds": Thresholds(
            p50_overhead_pct=p50_overhead_pct,
            p95_overhead_pct=p95_overhead_pct,
            error_delta_pct=error_delta_pct,
            entropy_metadata_rate_min=entropy_metadata_rate_min,
            min_throughput_delta_pct=min_throughput_delta_pct,
            max_error_rate_pct=max_error_rate_pct,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OptiLLM-on-MLX viability gates")
    parser.add_argument("--gate-config", help="Optional JSON config file. Supports top-level or viability_gate object.")

    parser.add_argument("--url", default=None)
    parser.add_argument("--models", default=None)
    parser.add_argument("--required-models", default=None)
    parser.add_argument("--concurrency-values", default=None)
    parser.add_argument("--prompts", help="Optional txt/jsonl prompt file")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--smoke-timeout", type=int, default=None)
    parser.add_argument("--bench-timeout", type=int, default=None)
    parser.add_argument("--bearer")
    parser.add_argument("--output-dir", default=None)

    parser.add_argument("--check-upstream-patch", action="store_true")
    parser.add_argument("--patch-path", help="Optional path to server.diff for maintainability check")

    parser.add_argument("--quality-report", help="Optional JSON quality report with status=pass|fail|unverified")
    parser.add_argument("--quality-required", action="store_true")

    parser.add_argument("--p50-overhead-pct", type=float, default=None)
    parser.add_argument("--p95-overhead-pct", type=float, default=None)
    parser.add_argument("--error-delta-pct", type=float, default=None)
    parser.add_argument("--entropy-metadata-rate-min", type=float, default=None)
    parser.add_argument("--min-throughput-delta-pct", type=float, default=None)
    parser.add_argument("--max-error-rate-pct", type=float, default=None)
    args = parser.parse_args()

    profile, profile_base = _resolve_gate_profile(args.gate_config)
    effective = _resolve_effective_inputs(args, profile, profile_base)

    models: List[str] = effective["models"]
    required_models: List[str] = effective["required_models"]
    concurrencies: List[int] = effective["concurrency_values"]

    if not models:
        raise SystemExit("--models cannot be empty")
    if not concurrencies:
        raise SystemExit("--concurrency-values cannot be empty")

    thresholds: Thresholds = effective["thresholds"]

    scripts_dir = Path(__file__).resolve().parent
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    work_dir = Path(str(effective["output_dir"])).resolve() / f"optillm_mlx_viability_{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "generated_at": timestamp,
        "url": effective["url"],
        "models": models,
        "required_models": required_models,
        "concurrency_values": concurrencies,
        "thresholds": {
            "p50_overhead_pct": thresholds.p50_overhead_pct,
            "p95_overhead_pct": thresholds.p95_overhead_pct,
            "error_delta_pct": thresholds.error_delta_pct,
            "entropy_metadata_rate_min": thresholds.entropy_metadata_rate_min,
            "min_throughput_delta_pct": thresholds.min_throughput_delta_pct,
            "max_error_rate_pct": thresholds.max_error_rate_pct,
        },
        "quality_required": effective["quality_required"],
        "gate_config": str(args.gate_config) if args.gate_config else None,
        "smoke": {},
        "benchmarks": {},
        "model_gate_status": {},
        "quality": {"status": "unverified", "reason": "quality not evaluated"},
        "maintainability": {"status": "unverified", "reason": "check not requested"},
    }

    for model in models:
        smoke = run_smoke(
            scripts_dir=scripts_dir,
            url=str(effective["url"]),
            model=model,
            max_tokens=int(effective["max_tokens"]),
            timeout=int(effective["smoke_timeout"]),
            bearer=effective["bearer"],
        )
        report["smoke"][model] = {
            "functional_pass": smoke["functional_pass"],
            "functional_status": smoke["functional_status"],
            "behavior_changed": smoke["behavior_changed"],
            "returncode": smoke["returncode"],
        }

        bench_model: Dict[str, Any] = {}
        bench_evals: List[Dict[str, Any]] = []
        for concurrency in concurrencies:
            bench = run_bench(
                scripts_dir=scripts_dir,
                url=str(effective["url"]),
                model=model,
                prompts=effective["prompts"],
                repeats=int(effective["repeats"]),
                max_tokens=int(effective["max_tokens"]),
                timeout=int(effective["bench_timeout"]),
                concurrency=concurrency,
                bearer=effective["bearer"],
                work_dir=work_dir,
            )
            eval_result = evaluate_bench_result(bench, thresholds)
            bench_model[str(concurrency)] = {
                "returncode": bench["returncode"],
                "summary_path": bench["summary_path"],
                "evaluation": eval_result,
            }
            bench_evals.append(eval_result)

        report["benchmarks"][model] = bench_model
        model_status = aggregate_model_status(smoke, bench_evals)
        report["model_gate_status"][model] = model_status

    if effective["check_upstream_patch"]:
        patch_path = effective["patch_path"]
        if patch_path is None:
            patch_path = str((scripts_dir.parent / "runtime" / "patches" / "mlx_lm" / "server.diff").resolve())
        report["maintainability"] = maybe_check_patch_rebase(Path(str(patch_path)))

    model_statuses = {
        model: str(payload.get("status", "unverified"))
        for model, payload in report["model_gate_status"].items()
    }

    final_decision, reasons = decide_final_status(
        model_statuses=model_statuses,
        required_models=required_models,
    )

    quality_report: Dict[str, Any] | None = None
    quality_load_error: str | None = None
    if effective["quality_report"]:
        quality_path = Path(str(effective["quality_report"]))
        if quality_path.exists():
            quality_report = _load_json_file(quality_path)
        else:
            quality_load_error = f"quality report not found: {quality_path}"

    quality = evaluate_quality_gate(quality_report, bool(effective["quality_required"]))
    if quality_load_error is not None:
        quality["status"] = "unverified"
        quality["reason"] = quality_load_error
    report["quality"] = quality

    quality_status = quality.get("status")
    if quality_status == "fail":
        final_decision = DECISION_NO_GO
        reasons.append("quality gate failed")
    elif quality_status == "unverified" and bool(effective["quality_required"]):
        if final_decision != DECISION_NO_GO:
            final_decision = DECISION_UNVERIFIED
        reasons.append("required quality gate unverified")
    elif quality_status == "skipped":
        if final_decision == DECISION_GO:
            final_decision = DECISION_CONDITIONAL_GO
        reasons.append("quality gate skipped")

    if report["maintainability"].get("status") == "fail":
        final_decision = DECISION_NO_GO
        reasons.append("maintainability check failed")

    if report["maintainability"].get("status") == "unverified":
        if final_decision == DECISION_GO:
            final_decision = DECISION_CONDITIONAL_GO
        reasons.append("maintainability check unverified")

    report["final_decision"] = final_decision
    report["decision_reasons"] = reasons

    out_path = work_dir / "viability_report.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({
        "final_decision": final_decision,
        "report_path": str(out_path),
        "decision_reasons": reasons,
    }, indent=2))

    if final_decision == DECISION_GO:
        return 0
    if final_decision == DECISION_CONDITIONAL_GO:
        return 3
    if final_decision == DECISION_UNVERIFIED:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
