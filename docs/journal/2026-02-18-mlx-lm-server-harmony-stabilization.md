# 2026-02-18 — MLX-LM server Harmony stabilization (backend + gateway)

## Goal / question
Stabilize `fast/main/deep/boost/boost-deep` so Open WebUI no longer shows Harmony/control artifacts
or leaked internal planning text while keeping `mlx_lm.server` as the active Studio backend.

## Symptoms observed
- `fast` intermittently returned internal planning text (e.g., "User says ...").
- `deep`/`fast` sometimes emitted Harmony protocol blocks in client-visible content.
- `main` frequently returned unrelated canned text about `chat_template.jinja`.
- Runtime drift appeared between `mlx_lm.server` and legacy `mlx-openai-server` processes.

## Root causes
- Model artifact issue: prior `main` lane snapshot (`LibraxisAI/Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4`)
  behaved as contaminated/unreliable for current usage.
- Runtime control drift: `mlxctl load` path launched legacy `mlx-openai-server` while launchd also started
  `mlx_lm.server`, creating mixed-process behavior.
- Studio launcher parser bug: registry rows were delimited by tab and parsed with shell `read`; empty fields
  collapsed, causing argument shifts (including misapplied `chat_template_args`).
- Gateway-only normalization was not sufficient for all non-Harmony "analysis leak" variants.

## Actions taken
- Replaced `main` runtime assignment with clean model:
  - `mlx-community/Qwen3-Next-80B-A3B-Instruct-4bit` on port `8101`.
- Normalized Studio runtime to `mlx_lm.server` only on active ports:
  - `8100` deep (`gpt-oss-120b`)
  - `8101` main (clean qwen)
  - `8102` fast (`gpt-oss-20b`)
- Patched Studio launcher `/opt/mlx-launch/bin/start.sh`:
  - switched row delimiter to unit-separator (`\x1f`) and matched `IFS` parser to preserve empty fields.
- Aligned launch behavior to `--use-default-chat-template` for active lanes to avoid broken explicit-template behavior.
- Updated LiteLLM mapping to `openai/default_model` for MLX lanes on fixed ports (`env.local`), preventing
  unintended upstream Hugging Face repo resolution attempts.
- Extended Harmony guardrail with leak-detection fallback for non-tag analysis spills.

## Validation snapshot
- Studio direct checks:
  - all active ports listening on `8100/8101/8102`.
  - direct chat probes returned expected short outputs.
- LiteLLM checks:
  - `fast/main/deep/boost/boost-deep` all returned valid outputs on smoke probes.
- Open WebUI:
  - user-confirmed behavior returned to normal after stabilization.

## Current contract (post-fix)
- Backend of record: `mlx_lm.server` (Studio launchd supervisor).
- Gateway of record: LiteLLM (`127.0.0.1:4000`) with Harmony guardrails (pre + post).
- Boost lanes: single Studio OptiLLM proxy with `boost` -> `main`, `boost-deep` -> `deep`.

## Follow-up guardrails
- Avoid mutating runtime with `mlxctl load` while backend migration is in-progress unless process-family impact is explicit.
- Keep launcher/parser changes under source control and verify with direct port probes after every restart.
- Keep gateway leak normalization as safety net; treat backend stability as primary control.
