# 2026-02-18 — mlxctl runtime alignment to mlx_lm.server

## Context
Studio inference runtime is currently `mlx_lm.server` on team lanes (`8100-8102`),
while parts of `mlxctl` still assumed `mlx-openai-server` process semantics.
This produced false negatives in `mlxctl verify` and reduced operator trust in
status/readiness checks.

## What changed
- Updated `mlxctl` runtime process detection to recognize both:
  - `mlx_lm.server`
  - `mlx-openai-server` (legacy fallback)
- Updated runtime model-path extraction to parse either:
  - `--model` (`mlx_lm.server`)
  - `--model-path` (`mlx-openai-server`)
- Updated `mlxctl verify` to use backend-aware runtime command parsing.
- Updated `mlxctl load` default launch backend to `mlx_lm.server`.
  - Legacy fallback remains available via `MLX_BACKEND=mlx-openai-server`.
- Extended `mlxctl status` with optional runtime checks:
  - `--checks`
  - `--json`

## Result
`mlxctl` now reflects actual Studio backend reality and can validate lane
assignments/path alignment without requiring legacy runtime assumptions.

## Follow-ups
- Add launchd reconciliation for `mlx_lm.server` lane units once runtime
  behavior is stable across reboot cycles.
- Expand smoke/readiness validation around output-quality leakage checks as
  part of normal post-change gates.
