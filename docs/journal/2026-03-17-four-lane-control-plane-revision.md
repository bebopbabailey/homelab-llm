# 2026-03-17 — Four-lane control-plane revision (`llmster` GPT family + MAIN fallback)

## Summary
- Implemented the repo contract for the approved four-lane LiteLLM architecture
  without mutating live services.
- Kept current public `main` / `deep` / `fast` behavior intact while adding the
  approved shadow/fallback contract for MAIN, HELPER, and the GPT lanes.
- Added the new repo-owned `layer-inference/llama-cpp-server/` service boundary
  for the `llmster`-backed llama.cpp GPT family.

## What changed
- Updated canonical docs and runtime-lock data to reflect:
  - MAIN target = `Qwen3-Next-80B-A3B-Instruct` on `vllm-metal`
  - MAIN explicit fallback = same Qwen family on `mlx-openai-server`
  - HELPER target = `Qwen3-4B-Instruct-2507`
  - FAST/DEEP target backend family = `llmster` / llama.cpp
- Added LiteLLM rollout aliases:
  - `main-shadow`
  - `main-fallback-shadow`
  - `helper`
  - `helper-shadow`
  - `fast-shadow`
  - `deep-shadow`
- Extended Studio scheduling policy to allowlist the approved rollout labels:
  - `com.bebop.mlx-shadow.8123`
  - `com.bebop.mlx-shadow.8124`
  - `com.bebop.mlx-shadow.8125`
  - `com.bebop.llmster-gpt.8126`
- Added a documentation-first launchd template for `com.bebop.llmster-gpt.8126`.

## Deliberate non-changes
- No live Studio labels were started or modified.
- No Mini or Studio services were restarted.
- No client-facing alias promotions were performed.
- `code-reasoning` remains a separate stable alias.
- `boost*` behavior remains unchanged.

## Next slice
- Validate `main-shadow` and `main-fallback-shadow` against the same boring
  contract before any `main` cutover.
- Keep FAST/DEEP behind the new `llmster` service boundary until their own
  acceptance gates are executed.
