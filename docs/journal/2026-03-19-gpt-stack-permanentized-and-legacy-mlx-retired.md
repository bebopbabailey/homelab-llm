# 2026-03-19 — GPT stack permanentized and legacy MLX rollback retired

## Summary
- Unloaded the old MLX GPT rollback lanes on Studio `8100` and `8102`.
- Kept the settled public runtime shape unchanged:
  `main` on MLX `8101`, `fast` + `deep` on shared `llmster` `8126`.
- Pruned stale GPT rollback artifacts and duplicate GPT weights so the Studio
  now keeps only active runtime model families for the settled stack.
- Updated repo truth so docs, runbooks, registries, and default validation
  paths no longer describe `8100` / `8102` as active GPT backends.

## Runtime actions
- Unloaded `8100` and `8102` through `mlxctl`, preserving `8101`.
- Left `8126` untouched as the canonical shared GPT service.
- Verified that public `main`, `fast`, and `deep` all still answered cleanly
  immediately after the MLX GPT lane retirement.

## Storage actions
- Extended the Studio model-retention tool to inventory:
  - `/Users/thestudio/models/hf`
  - `/Users/thestudio/.cache/huggingface/hub`
  - `/Users/thestudio/Library/Caches/llama.cpp`
  - `/Users/thestudio/.lmstudio/models`
- Changed the default keep-set so the Studio now retains only:
  - the active Qwen `main` MLX artifact
  - the active LM Studio GPT 20B GGUF artifact
  - the active LM Studio GPT 120B GGUF artifact
- Pruned the old MLX GPT rollback artifacts and stale GPT duplicates after the
  unload succeeded.

## Locked runtime reality
- Public aliases remain:
  - `main`
  - `fast`
  - `deep`
- Active public inference listeners are now:
  - MLX `8101` for `main`
  - `llmster` `8126` for `fast` + `deep`
- Retired public GPT rollback listeners:
  - `8100`
  - `8102`

## Follow-up
- No further work is required to make this settled stack permanent.
- Optional cleanup remains outside this slice:
  - stop the unexpected `8123` shadow listener if desired
  - resolve the unrelated OptiLLM runtime-lock drift
