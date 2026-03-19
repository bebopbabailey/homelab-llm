# FAST llmster 8126 Cutover Report

Date: 2026-03-18

## Scope
- This pass covered canonical `fast` only.
- `main` was out of scope.
- `deep` remained on MLX `8100`.
- LiteLLM on the Mini remained the public control plane.
- Studio `8126` was the production GPT service target.
- Raw `llama-server` mirrors stayed in scope as validation-only truth paths.

## Executive result
- `fast` was successfully cut over from MLX `8102` to Studio `8126` through LM Studio headless (`llmster`).
- The final public path is:
  - client/app -> LiteLLM on Mini -> `llmster` on Studio `8126` -> llama.cpp runtime
- The canonical backend model for `fast` is now:
  - `llmster-gpt-oss-20b-mxfp4-gguf`
- `deep` was intentionally not moved.

## What changed

### Studio storage
- A keep-set based retention pass was implemented and applied before runtime rollout.
- The keep-set for this slice was:
  - active `main` artifact
  - active MLX `fast` artifact
  - active MLX `deep` artifact
  - staged GPT-OSS 20B MXFP4 GGUF artifact
- Explicit delete-target families provided for this rollout were incorporated into the prune logic.

### Studio runtime
- Official LM Studio headless (`llmster`) was installed on Studio.
- The repo-owned `8126` service contract was aligned to the official `lms` path:
  - `/Users/thestudio/.lmstudio/bin/lms`
- The GPT-OSS 20B MXFP4 GGUF artifact was imported into LM Studio using a hard-link path rather than an unnecessary duplicate copy.
- The loaded Studio model identifier is:
  - `llmster-gpt-oss-20b-mxfp4-gguf`

### Validation path
- A raw `llama-server` mirror flow was added for direct truth-path validation.
- The raw fast mirror contract for this slice was:
  - Studio loopback `127.0.0.1:8130`
  - alias `llmster-gpt-oss-20b-mxfp4-gguf`

### Gateway path
- LiteLLM `fast` was repointed from MLX `8102` to Studio `8126`.
- The GPT harmony seam in LiteLLM was narrowed to make GPT-OSS behavior client-clean:
  - inject `reasoning_effort=low` when absent for GPT lanes
  - strip provider reasoning fields on GPT lane responses
- Existing `fast -> main` fallback was preserved.

## Canonical runtime identities

### Public alias
- `fast`

### Public backend endpoint
- `http://192.168.1.72:8126/v1`

### Public backend model
- `openai/llmster-gpt-oss-20b-mxfp4-gguf`

### Raw validation mirror
- `http://127.0.0.1:8130/v1`
- `llmster-gpt-oss-20b-mxfp4-gguf`

## Studio storage findings

### Before prune
- `/Users/thestudio/models` about `356G`
- `/Users/thestudio/.cache/huggingface` about `687G`
- `/Users/thestudio/Library/Caches/llama.cpp` about `11G`

### Dry-run retention manifest
- delete entries: `32`
- keep entries: `4`
- stage entries: `1`
- delete bytes: `1914864487113`
- keep bytes: `254286594634`
- stage bytes: `12109566560`

### After prune
- `/Users/thestudio/models` about `108G`
- `/Users/thestudio/.cache/huggingface` about `20G`
- `/Users/thestudio/Library/Caches/llama.cpp` about `11G`

### Active/staged keep-set after prune
- Qwen3-Next MLX artifact for `main`
- GPT-OSS 120B MLX artifact for current `deep`
- GPT-OSS 20B MLX artifact for rollback safety on `fast`
- GPT-OSS 20B MXFP4 GGUF artifact for `llmster`

## Studio runtime findings

### Hardware
- Mac Studio
- Apple M3 Ultra
- `256 GB` unified memory

### Raw llama.cpp binary
- path:
  - `/Users/thestudio/llama.cpp/build/bin/llama-server`
- version:
  - `8087 (e2f19b320)`

### LM Studio headless
- repo-assumed `lms` path was initially missing
- desktop app alone was not sufficient for headless operation
- official install path was required:
  - `curl -fsSL https://lmstudio.ai/install.sh | bash`
- resulting CLI path:
  - `/Users/thestudio/.lmstudio/bin/lms`
- resulting runtime:
  - `llmster v0.0.7+4`

### 20B MXFP4 artifact
- confirmed on disk at:
  - `/Users/thestudio/Library/Caches/llama.cpp/ggml-org_gpt-oss-20b-GGUF_gpt-oss-20b-mxfp4.gguf`

### 120B MXFP4 artifact
- not confirmed in the searched Studio cache paths during this slice
- this is the blocking dependency for the next `deep` rollout slice

## Direct backend findings

## Direct `llmster` on `8126`
Using the acceptance harness with the corrected GPT request shape:
- `reasoning_effort=low`
- non-stream Chat Completions

Results:
- plain chat: `5/5`
- structured simple: `5/5`
- auto tool noop: `9/10`
- auto tool arg-bearing: `9/10`
- concurrency smoke: pass

Important observation:
- without `reasoning_effort=low`, direct `8126` behavior was materially worse for plain chat and auto-tool prompts
- with `reasoning_effort=low`, direct `8126` became acceptable for this first production slice

## Raw `llama-server` mirror on `8130`
The raw mirror proved useful as a truth-path seam and showed the GPT-OSS request-shape sensitivity directly.

Observed behavior:
- plain chat became clean with `reasoning_effort=low`
- tool behavior on the raw mirror was directionally good but less boring than the final LiteLLM public path
- raw mirror remained a diagnostic seam, not the promotion target

Important interpretation:
- the public cutover was accepted on the public Mini gateway contract, not on the claim that raw mirror behavior was perfect on every stricter probe shape

## Public LiteLLM findings

### Final public `fast` contract
Public `fast` now routes to Studio `8126` and passed:
- plain chat: `5/5`
- structured simple: `5/5`
- auto tool noop: `10/10`
- auto tool arg-bearing: `8/10`
- concurrency smoke: pass

### Example visible behavior after cutover
- plain chat returns clean content such as `fast-ok`
- simple tool use returns proper `tool_calls`
- provider reasoning fields are no longer leaked to the client on the public GPT lane path

### Other aliases preserved
- `main` basic smoke: pass
- `deep` basic smoke: pass
- `/v1/models` still shows:
  - `deep`
  - `fast`
  - `main`

## Why the gateway seam needed adjustment
GPT-OSS behavior on this stack was not boring enough out of the box.

The observed issues were:
- reasoning-heavy chat output on direct `8126` when `reasoning_effort` was omitted
- direct backend responses carrying provider reasoning fields
- some stricter tool prompts degrading when response budget and reasoning behavior were not constrained

The adopted fix was deliberately narrow:
- keep the existing GPT harmony path in LiteLLM
- add `reasoning_effort=low` only when the caller did not provide one
- strip provider reasoning fields from GPT responses

This was enough to make the public `fast` path acceptable without redesigning LiteLLM or changing the client contract.

## Launch and lifecycle findings for `8126`

### Owned label
- `com.bebop.llmster-gpt.8126`

### Plist contract
- path:
  - `/Library/LaunchDaemons/com.bebop.llmster-gpt.8126.plist`
- command:
  - `/Users/thestudio/.lmstudio/bin/lms server start --bind 192.168.1.72 --port 8126`

### Important nuance
- `lms server start` returns successfully after ensuring the server is running
- the long-lived serving process remains managed under the LM Studio daemon
- launchd therefore records a successful short run rather than a classic foreground daemon lifetime
- despite that nuance, the server stayed up and continued serving `8126` correctly after the launchd-managed start

## Risks and residual gaps

### Accepted for this slice
- arg-bearing auto-tool use is acceptable but not perfect:
  - `8/10` through public LiteLLM
- raw mirror is a diagnostic seam, not a perfect promotion oracle on every harder prompt shape

### Not resolved in this slice
- `deep` is still on MLX because the `120B` MXFP4 GGUF artifact is not yet staged and dual-load posture was not validated
- the `8126` launch model is workable but has LM Studio daemon semantics rather than classic single-process service semantics

### Operational caution
- do not delete the MLX 20B rollback artifact until the observation window for `fast` is considered closed
- do not start `deep` migration until the `120B` MXFP4 GGUF artifact is staged and the shared `8126` listener posture is proven

## Final verdict
- `fast` is now canonical on Studio `8126` via `llmster`
- `deep` remains on MLX `8100`
- raw `8130` mirror remains part of the toolchain, but not part of steady-state production

## Next recommended step
- stage the GPT-OSS 120B MXFP4 GGUF artifact
- stand up the raw deep mirror on `127.0.0.1:8131`
- validate direct `8126` dual-load posture
- move `deep` only after raw mirror, direct `llmster`, and public LiteLLM all pass on the same evidence standard used for `fast`
