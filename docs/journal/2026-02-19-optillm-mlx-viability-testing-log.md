# 2026-02-19 — OptiLLM MLX viability testing log (entropy decoding)

## Context
This entry records the concrete execution history for the experimental
OptiLLM-on-MLX decode-time viability work (entropy decoding), not just the
test protocol.

Scope remained isolated to the experimental workspace and loopback endpoint.
No production lane ports/services were modified.

## Environment and scope
- Host used for orchestration and documentation: Mini (`/home/christopherbailey/homelab-llm`)
- Runtime target for primary viability evidence: Studio isolated endpoint
- Endpoint target for experiment: `127.0.0.1:8130` (`mlx_lm.server` patch workspace)
- Service boundary: `layer-inference/optillm-local`

## Test harness and commands used
- `uv run python layer-inference/optillm-local/scripts/smoke_decode.py ...`
- `uv run python layer-inference/optillm-local/scripts/bench_decode.py ...`
- `uv run python layer-inference/optillm-local/scripts/run_benchmark_matrix.py ...`
- `uv run python layer-inference/optillm-local/scripts/run_viability_gate.py ...`
- `uv run python layer-inference/optillm-local/scripts/run_viability_campaign.py ...`
- Unit tests:
  - `uv run python -m unittest layer-inference/optillm-local/tests/test_optillm_decoding.py`
  - `uv run python -m unittest layer-inference/optillm-local/tests/test_viability_gate.py`
  - `uv run python -m unittest layer-inference/optillm-local/tests/test_viability_campaign.py`

## Key viability reports (chronological)
- `/tmp/optillm_mlx_viability_20260218-183800/viability_report.json`
  - Decision: `UNVERIFIED`
  - Reason: required model `main` unverified; maintainability unverified
- `/tmp/optillm_mlx_viability_20260218-183805/viability_report.json`
  - Decision: `UNVERIFIED`
  - Reason: required model `main` unverified
- `/tmp/optillm_mlx_viability_20260218-193955/viability_report.json`
  - Decision: `UNVERIFIED`
  - Reason: required model `main` unverified; quality skipped; maintainability unverified
- `/tmp/optillm_mlx_viability_20260218-194051/viability_report.json`
  - Decision: `UNVERIFIED`
  - Reason: required model `main` unverified; required quality unverified
- `/tmp/optillm_mlx_viability_20260218-195127/viability_report.json`
  - Decision: `UNVERIFIED`
  - Reason: required model `main` unverified; quality skipped; maintainability unverified
- `/tmp/optillm_mlx_viability_20260218-214646/viability_report.json`
  - Decision: `CONDITIONAL_GO`
  - Reason: all model gates passed; quality skipped
- `/tmp/optillm_mlx_viability_20260218-230535/viability_report.json`
  - Decision: `GO`
  - Reason: all required and optional model gates passed; quality passed
- `/tmp/optillm_mlx_viability_20260219-000154/viability_report.json`
  - Decision: `NO_GO`
  - Reason: required `gpt-oss-20b` lane failed; quality gate failed

## Campaign runs captured in repo timeline
- `/tmp/optillm_mlx_campaign_20260219-134725/campaign_summary.json`
  - Decision: `UNVERIFIED` (`runs=1`)
- `/tmp/optillm_mlx_campaign_20260219-134744/campaign_summary.json`
  - Decision: `UNVERIFIED` (`runs=1`)
- `/tmp/optillm_mlx_campaign_20260219-134848/campaign_summary.json`
  - Decision: `UNVERIFIED` (`runs=1`)
  - Includes per-run logs:
    - `run_01/gate.stdout.log`
    - `run_01/gate.stderr.log`
    - `run_01/gate_output.json`

## Current truth from evidence
- Entropy decoding path is implemented and reachable in prior Studio runs.
- Viability is not yet stable across stronger validation profiles.
- Latest Mini-side campaign probes are `UNVERIFIED` due to required-model smoke
  unverified from this execution context.
- Most conservative current status remains: not yet proven viable for promotion.

## Next evidence required
- Repeat decision-profile campaign directly against verified reachable Studio
  isolated endpoint, with quality report supplied.
- Produce at least three consistent runs showing either stable `GO` or stable
  `NO_GO` before changing project direction.
