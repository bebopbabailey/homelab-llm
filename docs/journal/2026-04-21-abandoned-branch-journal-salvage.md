# 2026-04-21 - Abandoned branch journal salvage

## Source
- Branch: `rescue/root-pre-master-webreset-20260308-055303`
- Related branch: `wip/git-cleanup-20260304-162147`
- Purpose: preserve a journal correction from abandoned/unmerged branch history without editing the original append-only entry.

## Existing-entry correction
The abandoned branch modified `docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md`.
The original entry remains unchanged; the attempted correction is preserved below.

```diff
diff --git a/docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md b/docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md
index 0aa64db..0da2967 100644
--- a/docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md
+++ b/docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md
@@ -8,10 +8,10 @@ backend and preserving LiteLLM-first client routing.
 ## What changed
 1. Deterministic OptiLLM coding aliases (LiteLLM)
 - Added curated aliases in `layer-gateway/litellm-orch/config/router.yaml`:
-  - `boost-plan` -> `plansearch-openai/deep`
-  - `boost-plan-verify` -> `self_consistency-openai/deep`
-  - `boost-ideate` -> `moa-openai/deep`
-  - `boost-fastdraft` -> `bon-openai/fast`
+  - `boost-plan` -> `plansearch-deep`
+  - `boost-plan-verify` -> `self_consistency-deep`
+  - `boost-ideate` -> `moa-deep`
+  - `boost-fastdraft` -> `bon-fast`
 - Kept existing `boost` and `boost-deep` request-body behavior unchanged.
 
 2. Harmony normalization coverage
```
