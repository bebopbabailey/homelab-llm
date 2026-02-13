# 2026-02-11 - MLX runtime/boot single-contract on Studio

## Decision
- Studio MLX registry (`/Users/thestudio/models/hf/hub/registry.json`) is the
  single contract for both runtime and boot behavior.
- `mlxctl` remains the only supported control path for model/port changes.

## Why
- Drift was observed on port `8101`: live process model-path differed from
  registry assignment.
- Root cause was split authority between hardcoded launchd boot config and
  registry-managed runtime operations.

## Hardening
- `mlxctl verify` now checks assigned ports for runtime parity:
  - registry `cache_path` must match live `--model-path`.
- `mlxctl` now auto-defaults parser fields for `qwen3*` models:
  - `tool_call_parser: qwen3`
  - `reasoning_parser: qwen3`
  - optional local `chat_template` auto-discovery.

## Operational note
- Any boot script that hardcodes model assignments should be replaced with
  registry-driven startup to avoid reintroducing drift.
