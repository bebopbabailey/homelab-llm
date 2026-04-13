# Runbook: optillm-local (legacy experimental tooling)

Status: non-production; use for diagnostics/tuning only.

## Active workflow — vLLM-metal lane tuning

Phase A (full candidate sweep for a target lane):
```bash
uv run python experiments/legacy/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile experiments/legacy/optillm-local/config/viability_profiles/vllm_metal_lane_tuning.example.json \
  --out /tmp/vllm_metal_lane_tuning_report.json \
  --mode phaseA
```

Targeted main lane profile (`metal-test-main` on `8121`):
```bash
uv run python experiments/legacy/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile experiments/legacy/optillm-local/config/viability_profiles/vllm_metal_main_targeted_tuning.json \
  --out /tmp/vllm_metal_main_targeted.out.json \
  --mode phaseA
```

Targeted fast lane profile (`metal-test-fast` on `8120`):
```bash
uv run python experiments/legacy/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile experiments/legacy/optillm-local/config/viability_profiles/vllm_metal_fast_targeted_tuning.json \
  --out /tmp/vllm_metal_fast_targeted.out.json \
  --mode phaseA
```

Targeted deep lane profile (`metal-test-deep` on `8122`):
```bash
uv run python experiments/legacy/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile experiments/legacy/optillm-local/config/viability_profiles/vllm_metal_deep_targeted_tuning.json \
  --out /tmp/vllm_metal_deep_targeted.out.json \
  --mode phaseA
```

## Active workflow — failure probe
```bash
uv run python experiments/legacy/optillm-local/scripts/run_vllm_metal_failure_probe.py \
  --profile experiments/legacy/optillm-local/config/viability_profiles/vllm_metal_failure_probe.example.json \
  --out /tmp/vllm_metal_failure_probe.json
```

## Legacy workflow (historical reference)
Legacy `mlx_lm.server` decode-time patch experiments are retained in:
- `runtime/patches/mlx_lm/`
- `scripts/bootstrap_mlx_optillm_workspace.sh`

These legacy workflows are not the active runtime contract for current MLX team lanes.
