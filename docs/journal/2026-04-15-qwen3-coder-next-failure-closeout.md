# 2026-04-15 — Qwen3-Coder-Next backend experiment failure closeout

## Summary
- Closed out the `Qwen3-Coder-Next` backend experiment as a failed project.
- No public lane, trusted constrained-tool lane, or gateway contract changed as
  a result of this work.
- The experiment is abandoned in favor of a new, separate `Qwen Agent` project
  on the existing accepted lane.

## What we actually tried
- Apple `vllm-metal` direct shadow validation on Studio loopback:
  - runtime: `vllm 0.19.0`, `vllm-metal 0.1.0`
  - flags: `--enable-auto-tool-choice`, `--tool-call-parser qwen3_coder`,
    `--max-model-len 32768`, `--generation-config vllm`,
    `--no-async-scheduling`
  - no LiteLLM, no Open WebUI, no posthook salvage, no custom parser plugin
- Candidate artifacts tested on that direct path:
  - `mlx-community/Qwen3-Coder-Next-4bit`
  - `lmstudio-community/Qwen3-Coder-Next-MLX-6bit`
- Separate llama.cpp shadow preparation was started, but never reached runtime
  probing:
  - official `Qwen/Qwen3-Coder-Next-GGUF` `Q5_K_M` was downloaded
  - no raw `8132` mirror was launched
  - no `8133` llmster shadow was launched
  - no llama.cpp direct protocol evidence was gathered

## What we found
### Apple `vllm-metal` path
- `tool_choice="auto"` on `/v1/chat/completions` passed natively on both tested
  artifacts with populated structured `tool_calls` and valid JSON args.
- Named forced-tool failed on both tested artifacts:
  - `HTTP 200`
  - function name stayed correct
  - `tool_calls[0].function.arguments` contained raw XML-ish tool markup rather
    than valid JSON
  - the response was not callable without salvage
- `tool_choice="required"` failed on both tested artifacts:
  - `HTTP 200`
  - terminal reason reported tool use
  - `tool_calls` was empty
  - no callable protocol object existed
- `/v1/responses` was intentionally not evaluated further because the direct
  chat gate failed first.
- Conclusion: the current Apple `vllm-metal` path is not trustworthy for the
  constrained coding-agent control contract required here.

### llama.cpp / llmster path
- There is **no runtime result** to claim.
- The only true statement is that the official `Q5_K_M` GGUF was staged on
  Studio and the direct probe harness was scaffolded in the abandoned worktree.
- Since the raw mirror was never launched, this path must be treated as
  untested, not failed.

## Live system state at closeout
- No shadow listeners remained active on `8132` or `8133`.
- The shared trusted GPT `llmster` service on `8126` still had only:
  - `llmster-gpt-oss-20b-mxfp4-gguf`
  - `llmster-gpt-oss-120b-mxfp4-gguf`
- No public alias, gateway route, or accepted runtime lock changed.

## Residue to remove
- Studio caches from the abandoned project:
  - official GGUF cache for `Qwen3-Coder-Next-Q5_K_M`
  - Hugging Face hub metadata cache for `Qwen/Qwen3-Coder-Next-GGUF`
  - MLX coder caches:
    - `mlx-community/Qwen3-Coder-Next-4bit`
    - `lmstudio-community/Qwen3-Coder-Next-MLX-6bit`
  - matching lock directories and local tokenizer backup blobs created during
    the failed MLX packaging repair
- local scratch artifacts:
  - `/tmp/qwen3-coder-next-shadow-20260415`
  - `/tmp/qwen3-coder-next-llama-shadow`
- repo residue:
  - the dirty linked worktree
    `/home/christopherbailey/homelab-llm-qwen3-coder-next-lane-20260414`

## Final disposition
- Project status: failed and abandoned
- Promotion status: none
- Trusted constrained-tool lane: unchanged and still canonical
- Follow-up: start a separate `Qwen Agent` project on the existing accepted
  lane after the repo and Studio are returned to a boring clean baseline
