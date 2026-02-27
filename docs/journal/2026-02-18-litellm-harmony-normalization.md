# 2026-02-18 — LiteLLM Harmony normalization (gateway canonical layer)

## Context
- Studio backend was reset to stock `mlx_lm.server` lanes on `8100/8101/8102`.
- GPT-OSS lanes (`deep`, `fast`) leaked Harmony wire tags in output
  (`<|channel|>analysis ... <|channel|>final ...`).
- The key failure mode was turn-history poisoning: raw Harmony-tagged assistant text
  could be sent back upstream on later turns.

## Decision
- Keep backend stock.
- Move Harmony normalization to LiteLLM guardrails as the canonical layer.
- Scope normalization only to GPT lanes: `deep`, `fast`, `boost`, `boost-deep`.
- Keep `main` (Qwen lane) passthrough.
- Coerce GPT lanes to non-streaming at gateway for now.

## Changes
- `config/router.yaml`
  - enabled `litellm_settings.modify_params: true`.
  - passed Harmony guardrail parameters:
    - `target_models: "deep,fast,boost,boost-deep"`
    - `coerce_stream_false: true`
- `config/harmony_guardrail.py`
  - strict Harmony detection guard (`<|channel|>` + `<|message|>` + `analysis|final`)
  - pre-call:
    - mutate only `assistant` history turns
    - extract `final` content when strict Harmony payload is detected
    - force `stream=false` on targeted GPT lanes
  - post-call:
    - normalize strict Harmony responses to `final` only
    - passthrough for non-target lanes and non-Harmony text
  - removed heuristic fallback reply rewriting for non-Harmony text

## Expected runtime behavior
- GPT lanes:
  - no raw Harmony wire tags should surface to clients on non-stream calls.
  - prior assistant Harmony output should not poison subsequent turns.
- Qwen lane (`main`):
  - no Harmony normalization changes applied.

## Follow-up
- Re-evaluate streaming for GPT lanes after confirming deployed LiteLLM
  streaming hook behavior supports reliable post-processing.
