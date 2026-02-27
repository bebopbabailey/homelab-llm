# 2026-02-26 — vLLM-metal `8120` paged-attention workaround validation (`metal-test-fast`)

## Goal
Validate whether enabling paged attention provides a short-term overlap-concurrency
workaround for `metal-test-fast` (`8120`) after the prior KV-cache merge crash path.

## Scope and method
- Lane: `metal-test-fast` (`8120`) only.
- Transport: direct to `http://192.168.1.72:8120` (LiteLLM excluded from measurement loop).
- Harness: `layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py`.
- Fixed request shape retained from prior Phase A profile (`n=1`, warmup+quiescence gates).

## Control rerun (non-paged)
- Profile: `layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_targeted_tuning.json`
- Artifacts:
  - `/tmp/vllm_metal_fast_control.json`
  - `/tmp/vllm_metal_fast_control.md`
- Result:
  - all candidates failed at `concurrency=2` with `EngineCore encountered an issue`
  - confirms previous overlap instability persists on default cache path.

## Paged-attention workaround runs
### Attempt 1 (`memory_fraction=0.60`)
- Initial paged profile launch failed during engine startup with:
  - `ValueError: Paged attention: requested memory exceeds available RAM`
- Log guidance suggested lowering memory fraction (<= `0.48`).

### Attempt 2 (`memory_fraction=0.40`)
- Profile used:
  - `layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_paged_targeted_tuning.json`
- Artifacts:
  - `/tmp/vllm_metal_fast_paged.json`
  - `/tmp/vllm_metal_fast_paged.md`
- Startup succeeded and paged kernel initialized, but first warmup request failed.
- Repeated fatal signature in `/Users/thestudio/vllm-8120.log`:
  - `AttributeError: 'AttentionBlock' object has no attribute 'n_heads'`
  - stack includes `vllm_metal/metal_kernel_backend/paged_attention.py`.

## Findings
- Paged attention is currently **not a viable workaround** for this GPT-OSS fast lane.
- Failure moved from prior merge-broadcast path to a paged-kernel path (`n_heads`) and
  fails before overlap stages (warmup failure at `concurrency=1`).
- Therefore, this run did not recover overlap concurrency for `metal-test-fast`.

## Current lane posture (post-test)
- `8120` restored to known-good non-paged baseline:
  - `VLLM_METAL_MEMORY_FRACTION=0.60`
  - `--max-model-len 32768`
  - `--no-async-scheduling`
- Health checks:
  - `/health` returns 200
  - `/v1/models` returns `default_model`

## Evidence commands
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_targeted_tuning.json \
  --out /tmp/vllm_metal_fast_control.json \
  --mode phaseA

uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_paged_targeted_tuning.json \
  --out /tmp/vllm_metal_fast_paged.json \
  --mode phaseA

ssh studio "tail -n 220 /Users/thestudio/vllm-8120.log"
curl -fsS http://192.168.1.72:8120/health
curl -fsS http://192.168.1.72:8120/v1/models | jq .
```

## Outcome
- Status: PASS (workaround test executed and codified)
- Decision: keep `metal-test-fast` on non-paged path and treat overlap as constrained
  pending upstream `vllm-metal` fixes for GPT-OSS paged and merge paths.
