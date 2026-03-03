# 2026-03-02 — mlxctl vLLM flag compiler + `main` lane auto-tool enablement

## Summary
- Added a strict shared `vllm-metal` launch-arg compiler in `mlxctl`.
- Added operator commands:
  - `mlxctl vllm-capabilities`
  - `mlxctl vllm-render`
  - `mlxctl vllm-set`
- Updated team-lane launch path (`mlx-launch-start`) to consume rendered args
  and enforce fail-closed validation for unsupported auto-tool/parser settings.
- Enabled staged auto-tool behavior for `main` lane (`8101`) with parser alias
  resolution (`qwen3` -> `qwen3_xml` on current Studio vLLM build).

## Why
OpenCode and similar clients issue `tool_choice:"auto"` by default. The prior
team-lane launch path omitted required vLLM flags for Qwen3 auto tool calling,
causing request failures on `main`.

## Implementation details
- New nested registry contract support: `model.vllm.{profile,tool_choice_mode,tool_call_parser,reasoning_parser,max_model_len,memory_fraction,async_scheduling}`
  with backward-compatible read fallback from flat legacy keys.
- Added capability discovery from `vllm serve --help=all` and parser enum parsing.
- Added strict parser compatibility mapping for logical `qwen3`.
- `verify` now compiles effective lane config for team ports and fails on invalid
  auto-tool/parser config.

## Validation
- `uv run python -m py_compile platform/ops/scripts/mlxctl` ✅
- `uv run python -m unittest discover -s platform/ops/scripts/tests -p 'test_mlxctl_vllm_flags.py'` ✅
- `./platform/ops/scripts/mlxctl studio-cli-sha` (mismatch) -> `sync-studio-cli` -> `studio-cli-sha` (match) ✅
- `./platform/ops/scripts/mlxctl vllm-capabilities --json` ✅
- `./platform/ops/scripts/mlxctl vllm-render --ports 8101 --validate --json` ✅
  - rendered args include:
    - `--enable-auto-tool-choice`
    - `--tool-call-parser qwen3_xml`
    - `--reasoning-parser qwen3`
- `./platform/ops/scripts/mlxctl mlx-launch-stop --ports 8101` ✅
- `./platform/ops/scripts/mlxctl mlx-launch-start --ports 8101` ✅
- `ssh studio "ps -eo pid,command | rg -- '--port 8101|enable-auto-tool-choice|tool-call-parser qwen3_xml'"` ✅
- `./platform/ops/scripts/mlxctl verify` ✅
- Direct Studio `8101` chat completion with `tool_choice:"auto"` ✅ (HTTP 200)
- LiteLLM `model:"main"` chat completion with `tool_choice:"auto"` ✅ (HTTP 200)

## Scope notes
- Team lane policy remains unchanged: `8100-8119` are `mlxctl`-managed.
- No new ports/binds/LAN exposure introduced.
- Deep/Fast lane behavior remains unchanged in this phase; `main` was staged first.
