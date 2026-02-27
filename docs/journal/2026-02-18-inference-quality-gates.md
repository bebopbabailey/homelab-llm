# 2026-02-18 — Inference quality gates for Studio MLX lanes

## Context
With Studio runtime aligned on `mlx_lm.server` and `mlxctl` parity restored,
we needed a durable way to verify inference output quality (not just listener
health) after reboot, model swaps, and config changes.

## Added
- Fixture: `layer-inference/docs/fixtures/inference_golden_smoke.json`
  - lane-specific smoke prompts for `deep/main/fast`
  - forbidden protocol leakage markers (`<|channel|>`, `<think>`, tool tags)
- Script: `platform/ops/scripts/mlx_quality_gate.py`
  - resolves lane model id via `/v1/models`
  - runs short chat/completion smoke request per lane
  - fails on timeout, empty output, or forbidden markers
  - supports `--json` output for machine-readable automation

## Run sequence (FAST)
```bash
mlxctl status --checks
mlxctl verify
uv run python /home/christopherbailey/homelab-llm/platform/ops/scripts/mlx_quality_gate.py --host 192.168.1.72 --json
```

## Baseline result (first run)
- `total=3`, `passed=1`, `failed=2`
- `main` passed
- `deep` and `fast` failed due to raw protocol leakage markers:
  - `<|channel|>`, `<|message|>`, `<|start|>`, `<|end|>`
- This confirms the gate is correctly catching Harmony-leak regressions that still need mitigation.

## Docs updated
- `docs/foundation/testing.md`
- `docs/foundation/mlx-registry.md`
- `layer-inference/RUNBOOK.md`
- `NOW.md`

## Intent
Make output quality checks an explicit operational gate so regressions are
caught early and consistently across `fast/main/deep`.
