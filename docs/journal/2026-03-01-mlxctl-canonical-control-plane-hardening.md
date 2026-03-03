# 2026-03-01 — mlxctl canonical control-plane hardening

## Why
`mlxctl` had drift risk between the repo script and `/Users/thestudio/bin/mlxctl`,
plus stale command guidance (`mlxctl ensemble`) and a stale healthcheck assumption
(single-lane `8100` check).

## What changed
1. CLI parity gate + sync tools
- Added `mlxctl studio-cli-sha` and `mlxctl sync-studio-cli`.
- Mutating commands are parity-gated unless `MLXCTL_ENFORCE_REMOTE_PARITY=0`.

2. Team-lane mutation alignment with per-lane launchd
- `load` on team ports (`8100-8119`) now updates registry and restarts the
  specific lane via launchd (`mlx-launch-start --ports <port>` path).
- `unload`/`unload-all` stop team ports via lane labels; experimental ports keep
  direct process stop behavior.
- `mlx-launch-start` now supports `--ports` for port-scoped application.

3. CLI ergonomics and safety
- `status --json` is now JSON-only; `--table` restores mixed output.
- Status state names changed to `listening|running|idle`, with
  `listener_visible` in JSON.
- Omni numeric flags use typed argparse values (no Python traceback on invalid ints).
- `verify` is read-only by default; `verify --fix-defaults` enables persistence.
- `assign-team --dry-run` no longer runs remote `init` and `_apply_port_map`
  now fails fast on load errors.
- `mlx-launch-configure-vllm` is guarded as legacy via `MLX_ALLOW_LEGACY=1`.

4. Documentation/runtime alignment
- Updated `docs/foundation/mlx-registry.md` and `docs/foundation/testing.md` for
  parity gate + status/verify contract changes.
- Updated `layer-inference/RUNBOOK.md` to include parity check/sync before lane mutations.
- Updated `AGENTS.md` root MLX guardrail with parity requirement.
- Updated `layer-gateway/optillm-proxy/AGENTS.md` to remove deprecated
  `mlxctl ensemble` helpers.
- Updated `platform/ops/scripts/healthcheck.sh` to dynamically validate all
  active team lanes from `mlxctl status --json`.

## Verification highlights
- `mlxctl studio-cli-sha` reports match after sync.
- Parity mismatch blocks mutating commands with remediation instructions.
- `status --json` emits pure JSON.
- `load ... 8102 --force --ignore-launchd --no-sync` completes via lane restart path.
- `mlxctl verify` passes after changes.

## Follow-up hardening (same day)
1. `reconcile` safety contract
- `mlxctl reconcile` now defaults to dry-run and never mutates unless `--apply` is passed.
- Stale detection requires all three signals to fail before clearing:
  no listener, no runtime process, and failed local `/v1/models` probe.
- Added structured output: `mlxctl reconcile --json`.

2. Studio target normalization
- Parity/sync/forwarding paths now resolve Studio target from a shared helper,
  reducing drift risk between `STUDIO_HOST` and `STUDIO_SSH` usage.

3. Documentation alignment
- Updated testing/runbook examples for safe reconcile usage.
- Corrected GPT-OSS fast lane example to use `8102` for
  `mlx-gpt-oss-20b-mxfp4-q4`.
