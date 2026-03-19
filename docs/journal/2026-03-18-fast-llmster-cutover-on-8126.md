# 2026-03-18 — `fast` llmster cutover on `8126`

## Summary
- Pruned Studio model storage down to the active keep-set plus the staged GPT-OSS
  20B MXFP4 GGUF artifact.
- Installed official LM Studio headless (`llmster`) on Studio and loaded
  `gpt-oss-20b` under identifier `llmster-gpt-oss-20b-mxfp4-gguf`.
- Stood up the raw `llama-server` truth-path mirror on `127.0.0.1:8130`.
- Repointed public LiteLLM alias `fast` from MLX `8102` to Studio `8126`.

## Runtime contract
- Public path:
  - Mini LiteLLM `fast` -> `http://192.168.1.72:8126/v1`
  - backend model `openai/llmster-gpt-oss-20b-mxfp4-gguf`
- Studio service:
  - label `com.bebop.llmster-gpt.8126`
  - bind `192.168.1.72:8126`
- Raw truth path:
  - `127.0.0.1:8130`
  - alias `llmster-gpt-oss-20b-mxfp4-gguf`

## Important behavior notes
- GPT-OSS chat/tool behavior required `reasoning_effort=low` for stable
  non-stream Chat Completions behavior on this slice.
- LiteLLM harmony pre-call now injects `reasoning_effort=low` for GPT lanes when
  absent.
- LiteLLM harmony post-call now strips provider reasoning fields from GPT lane
  responses.

## Validation
- Studio prune manifest:
  - delete candidates applied: `32`
  - post-prune storage:
    - `/Users/thestudio/models` about `108G`
    - `~/.cache/huggingface` about `20G`
    - `~/Library/Caches/llama.cpp` about `11G`
- Direct `llmster` on `8126`:
  - plain chat: `5/5`
  - structured simple: `5/5`
  - auto tool noop: `9/10`
  - auto tool arg-bearing: `9/10`
  - concurrency smoke: pass
- Public LiteLLM `fast`:
  - plain chat: `5/5`
  - structured simple: `5/5`
  - auto tool noop: `10/10`
  - auto tool arg-bearing: `8/10`
  - concurrency smoke: pass

## Known gaps
- Raw `8130` mirror remains a diagnosis seam, but the stricter argument-bearing
  and structured-output probes were less stable than the public LiteLLM path on
  this first slice.
- `deep` remains on MLX `8100` pending the `120B` MXFP4 GGUF artifact and
  shared-listener validation.

## Outcome
- `fast` is now canonical on Studio `8126` through `llmster`.
- `deep` remains on MLX.
