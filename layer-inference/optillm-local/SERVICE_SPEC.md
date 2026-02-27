# Service Spec: optillm-local (experimental tooling workspace)

## Purpose
Provide reproducible, non-production tooling for inference experiments, with
primary emphasis on Studio `vllm-metal` lane diagnostics and tuning.

## Status
- Not deployed as an always-on production service.
- Tooling-only boundary (scripts + profiles + reports).

## Active interfaces
- Harness CLI: `scripts/run_vllm_metal_lane_tuning.py`
  - Inputs: JSON profile + mode (`phaseA|phaseB|all`)
  - Outputs: JSON report + markdown scorecard
- Probe CLI: `scripts/run_vllm_metal_failure_probe.py`
  - Inputs: profile describing request shape + target lane
  - Outputs: failure forensics bundle

## Legacy interfaces (historical, retained)
- `mlx_lm.server` patch-overlay workflow under `runtime/patches/mlx_lm/`.
- Loopback decode-time experiments via `scripts/bootstrap_mlx_optillm_workspace.sh`.
- Not part of the active team-lane runtime contract.

## Safety gates
- No LAN exposure changes from this workspace without explicit plan approval.
- Team lanes (`8100-8119`) remain controlled through `mlxctl`.
- Experimental lanes (`8120-8139`) are valid targets for tuning/probing.
