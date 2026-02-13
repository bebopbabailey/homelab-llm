# 2026-02-11 - MLXCTL GPT-OSS auto-harmony defaults

## Context
- A new GPT-OSS 120B variant loaded on Studio port `8100` returned raw Harmony
  channel tags (for example `<|channel|>analysis`) in `message.content`.
- Root cause: `mlxctl` only passed parser/template args when the registry entry
  already included those fields.

## Changes
- Updated `platform/ops/scripts/mlxctl` to auto-detect GPT-OSS entries and
  persist safe defaults:
  - `tool_call_parser: harmony`
  - `reasoning_parser: harmony`
  - `chat_template` resolved from template fallbacks under
    `/opt/mlx-launch/templates` (or `MLX_TEMPLATE_DIR`).
- `mlxctl init` now backfills defaults for existing entries too.
- `mlxctl verify` now validates GPT-OSS Harmony fields and template-path
  existence, and writes auto-filled defaults back to registry.
- `mlxctl load` now runs a lightweight Harmony smoke check and warns if raw
  `<|channel|>` leakage is detected.

## Validation
- Local script checks:
  - `python3 -m py_compile platform/ops/scripts/mlxctl`
  - `platform/ops/scripts/mlxctl --help`
- Studio runtime checks:
  - `ssh studio '/Users/thestudio/bin/mlxctl --local verify'`
  - `ssh studio '/Users/thestudio/bin/mlxctl --local load txgsync-gpt-oss-120b-derestricted-mxfp4-mlx 8100 --force --ignore-launchd --no-sync'`
  - `curl` chat completion on `8100` to confirm no raw Harmony tags.

## Notes
- This keeps behavior durable for new GPT-OSS variants without requiring manual
  registry edits each time.
