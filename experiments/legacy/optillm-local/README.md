# optillm-local (Legacy Inference Experiments)

Status: historical non-production workspace retained for reference and selective diagnostics.

This service boundary contains experimental tooling only. Current active use is
`vllm-metal` lane diagnostics/tuning on Studio experimental ports, plus retained
legacy artifacts for earlier `mlx-lm` decode-time patch research.

## Current focus (active)
- `vllm-metal` lane failure probes and targeted tuning harnesses.
- Fixed-shape stability/perf sweeps for `metal-test-*` lanes.
- JSON + markdown result artifacts for reproducible decisions.

## Legacy track (retained for reference)
- `mlx-lm` patch overlay and decode-time viability gate artifacts.
- Experimental loopback server workflow (`8130`) from earlier research.
- These legacy assets are not the active runtime contract for team lanes.

## Entry points
- Tuning harness: `scripts/run_vllm_metal_lane_tuning.py`
- Failure probe: `scripts/run_vllm_metal_failure_probe.py`
- Profiles: `config/viability_profiles/`
- Legacy patch overlay: `runtime/patches/mlx_lm/`
- Legacy bootstrap script: `scripts/bootstrap_mlx_optillm_workspace.sh`
