# Apple MLX / vLLM / GPT-OSS Runtime Review

Date: 2026-03-13  
Scope: Apple Silicon inference runtime strategy for GPT-OSS and adjacent model families on the Studio  
Audience: senior developer review and follow-on runtime design work  
Status: research handoff, no runtime changes made

## Executive Summary

The current Studio inference stack is not a pure MLX serving path. It is a `vllm-metal` path serving MLX-format model artifacts under `mlxctl` and per-lane launchd labels.

That distinction matters:

- the stack is already Apple-native enough to benefit from MLX-format artifacts, unified memory, and GPT-OSS's strong MXFP4 fit
- it is not a fully pure MLX decode loop
- the production runtime is intentionally conservative, with paged attention and async scheduling disabled

The main conclusions from this research are:

- GPT-OSS remains the strongest family on this stack in quality-per-gig terms.
- The current production path for GPT-OSS should remain `vllm-metal`.
- Pure MLX is worth reconsidering only as a canary, not as a blind production swap.
- If pure MLX is revisited, `gpt-oss-20b` is the correct first target, not `gpt-oss-120b`.
- Of the pure-MLX-serving options researched, `mlx-openai-server` is currently the most serious candidate for a GPT-OSS canary because it now has queueing, concurrency controls, prompt-cache knobs, speculative decoding, and modern OpenAI-style APIs.
- There is not enough evidence from current upstream docs to claim that `mlx-openai-server` matches vLLM on continuous batching, automatic prefix caching, or scheduler sophistication.

The ranked recommendation at this point is:

1. keep `gpt-oss-120b` on `vllm-metal`
2. keep `gpt-oss-20b` on `vllm-metal` in production
3. if pure MLX is revisited, use `gpt-oss-20b` first and use `mlx-openai-server` before bare `mlx_lm.server`
4. treat `main` model-family replacement as a separate question from the GPT-OSS runtime question

## Questions This Report Answers

- What is the current runtime truth on the Studio?
- Are we actually getting MXFP4 benefits in the current architecture?
- Is the current setup "optimized for Apple" or only "compatible with Apple"?
- What does `vllm-metal` buy us relative to pure MLX?
- Has `mlx-openai-server` matured enough to be worth reconsidering?
- Why is `gpt-oss-20b` the right pure-MLX canary instead of `gpt-oss-120b`?
- Which model families look strongest for `vLLM` and `vllm-metal` on this stack?
- What should another senior engineer verify or challenge next?

## Current Local Runtime Truth

### Active lane mapping

Current logical alias mapping:

- `deep` -> `8100` -> `mlx-gpt-oss-120b-mxfp4-q4`
- `main` -> `8101` -> `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
- `fast` -> `8102` -> `mlx-gpt-oss-20b-mxfp4-q4`

Canonical local sources:

- [docs/foundation/mlx-registry.md](/home/christopherbailey/homelab-llm/docs/foundation/mlx-registry.md)
- [docs/INTEGRATIONS.md](/home/christopherbailey/homelab-llm/docs/INTEGRATIONS.md)
- [platform/ops/runtime-lock.json](/home/christopherbailey/homelab-llm/platform/ops/runtime-lock.json)

### Runtime family

The active runtime family for team lanes is:

- `vllm-metal`

This is not a speculative conclusion. It is explicit in the repo's current sources of truth:

- [docs/foundation/mlx-registry.md](/home/christopherbailey/homelab-llm/docs/foundation/mlx-registry.md)
- [layer-inference/RUNBOOK.md](/home/christopherbailey/homelab-llm/layer-inference/RUNBOOK.md)
- [layer-gateway/litellm-orch/decision-log.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/decision-log.md)
- [platform/ops/README.md](/home/christopherbailey/homelab-llm/platform/ops/README.md)

### Current runtime lock posture

The current lock posture for MLX team lanes is conservative:

- `paged_attention=false`
- `async_scheduling=false`
- `memory_fraction=auto`

For `8101`, the current active lock override keeps:

- `tool_choice_mode=auto`
- `tool_call_parser=hermes`
- `reasoning_parser=null`

Canonical source:

- [platform/ops/runtime-lock.json](/home/christopherbailey/homelab-llm/platform/ops/runtime-lock.json)

### Hardware and artifact size facts

Local read-only checks confirmed:

- Studio host: Apple M3 Ultra
- unified memory: 256 GB
- current active snapshot sizes:
  - `gpt-oss-120b`: about `58G`
  - `gpt-oss-20b`: about `10G`
  - current Qwen `main`: about `39G`

These numbers are useful as practical "resting artifact" proxies, not as exact live resident-memory measurements.

### Current implication

The current production runtime is best described as:

- Apple-native MLX-format artifacts
- served by `vllm-metal`
- under a conservative ops contract
- not a pure MLX decode loop

## What MXFP4 Is Buying Today

## Quality and fit benefits

Yes, the current architecture is getting real MXFP4 benefits.

The most important fact is that GPT-OSS is not just a community after-the-fact low-bit conversion. OpenAI states that:

- GPT-OSS is released natively in MXFP4
- the MoE weights were post-trained with MXFP4 quantization

Primary sources:

- <https://openai.com/index/introducing-gpt-oss/>
- <https://cdn.openai.com/pdf/419b6906-9da6-406c-a19d-1bb078ac7637/oai_gpt-oss_model_card.pdf>

That means the current stack benefits from:

- strong quality-per-gig behavior
- better local fit than higher-precision equivalents
- unusually credible FP4 fidelity for an open model family

## What MXFP4 is not automatically buying

The current setup should not be interpreted as a perfect end-to-end native FP4 runtime.

Important distinctions:

- MLX recognizes `mxfp4` as a quantization mode.
- vLLM's current MXFP4 documentation still describes support as weight-oriented (`MXFP4A16`) rather than a fully enabled dynamic-activation path.

Primary sources:

- <https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html>
- <https://docs.vllm.ai/projects/llm-compressor/en/latest/experimental/mxfp4/>

### Clean interpretation

Current architecture is getting:

- fit benefits
- fidelity-per-gig benefits
- Apple viability

Current architecture is not proven to be getting:

- the fullest possible FP4 runtime path
- every theoretical serving benefit that a future, more native stack might deliver

## Pure MLX vs `vllm-metal`

This section separates three different things:

- `vllm-metal`
- `mlx-openai-server`
- `mlx_lm.server` / raw `mlx-lm`

They are not interchangeable.

## `vllm-metal`

### What it is

`vllm-metal` is the current production backend shape for Studio team lanes.

It combines:

- vLLM serving architecture
- MLX/Metal compute backend
- an OpenAI-compatible server surface

Primary sources:

- <https://github.com/vllm-project/vllm-metal>
- [docs/foundation/mlx-registry.md](/home/christopherbailey/homelab-llm/docs/foundation/mlx-registry.md)

### What it buys

From current upstream docs and README material, `vllm-metal` is attractive because it aims to keep:

- vLLM engine and scheduler behavior
- unified-memory-friendly serving on Apple
- OpenAI-compatible APIs
- experimental paged-attention support

The repo's own current architecture intentionally standardized on this as the production runtime:

- [docs/foundation/mlx-registry.md](/home/christopherbailey/homelab-llm/docs/foundation/mlx-registry.md)
- [layer-gateway/litellm-orch/decision-log.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/decision-log.md)

### Current limitation

In this repo, many of the more aggressive vLLM knobs are not active:

- paged attention is off
- async scheduling is off
- the live render for GPT lanes is conservative

This is one of the main reasons the "vLLM should obviously win" argument is weaker in this specific deployment than it sounds in the abstract.

## `mlx-openai-server`

### What it is

`mlx-openai-server` is a pure-MLX-serving candidate that has evolved well beyond a minimal wrapper.

As of the current docs and PyPI release:

- it exposes OpenAI-style endpoints
- it supports the Responses API
- it supports structured outputs
- it supports tool calling and parser selection
- it supports multi-model serving
- it has explicit queue and concurrency settings
- it supports speculative decoding

Primary sources:

- <https://github.com/cubist38/mlx-openai-server>
- <https://pypi.org/project/mlx-openai-server/>

### What is clearly good now

This is the feature surface that makes it newly interesting:

- `max_concurrency`
- `queue_timeout`
- `queue_size`
- `prompt_cache_size`
- `prompt_cache_max_bytes`
- speculative decoding knobs
- parser / message-converter configuration
- subprocess isolation in multi-handler mode to avoid MLX/Metal resource problems

### What was not found in current docs

The current docs did not provide clear, explicit evidence of:

- continuous batching
- PagedAttention-style memory management
- APC-equivalent shared-prefix scheduler behavior

Important note:

- this is a documentation-backed limitation statement, not proof that some internal optimization does not exist
- but absent explicit documentation, another engineer should not assume parity with vLLM here

## `mlx_lm.server` / raw `mlx-lm`

### What it is

This is the purest MLX route of the three.

It is the best fit when you want:

- maximal control
- lowest abstraction
- direct access to MLX-LM behavior

### What it buys

The relevant MLX-LM capabilities for this discussion are:

- prompt caching
- rotating KV cache
- Apple-specific wired-memory tuning guidance

Primary source:

- <https://github.com/ml-explore/mlx-lm>

### Why it is not the default answer

In this repo, `mlx_lm.server` is no longer part of the active production contract.

The repo currently treats it as:

- legacy / fallback
- experimental workspace material
- not the canonical team-lane runtime

Local sources:

- [platform/ops/README.md](/home/christopherbailey/homelab-llm/platform/ops/README.md)
- [layer-inference/optillm-local/SERVICE_SPEC.md](/home/christopherbailey/homelab-llm/layer-inference/optillm-local/SERVICE_SPEC.md)
- [layer-inference/optillm-local/runtime/patches/mlx_lm/README.md](/home/christopherbailey/homelab-llm/layer-inference/optillm-local/runtime/patches/mlx_lm/README.md)

### Clean interpretation

`mlx_lm.server` is the highest-control and highest-burden path.

It is attractive if:

- you want to specialize hard for one workload shape
- you are comfortable owning more runtime behavior yourself

It is unattractive if:

- you want production-grade server ergonomics by default
- you want the strongest documented concurrency/scheduler story

## GPT-OSS Runtime Matrix

This is the runtime matrix that best captures the current recommendation.

| Option | Best workload shape | Why it might win | Why it might lose | Current verdict |
| --- | --- | --- | --- | --- |
| `gpt-oss-20b` on `vllm-metal` | mixed interactive coding, some concurrency, some repeated prefixes | strongest documented scheduler and prefix-cache story; current production home | current deployment is conservative, so the full vLLM advantage is not currently realized | best production default |
| `gpt-oss-20b` on `mlx-openai-server` | shared-prefix coding loops, single-user or light concurrency, Apple-first efficiency experiments | prompt-cache controls, queueing, speculative decoding, modern API surface, low blast radius | no documented continuous batching or APC-equivalent scheduler | best pure-MLX canary candidate |
| `gpt-oss-120b` on `vllm-metal` | expensive deep-thinking lane, heterogeneous prompts, higher cost of misses | vLLM's scheduler and cache architecture matter most here | Apple plugin maturity and conservative current lock reduce theoretical upside | best production home for 120b today |
| `gpt-oss-120b` on `mlx-openai-server` | mostly single-user, repeated huge prefixes, low-diversity deep work | could benefit from MLX-native prompt caching and Apple-specific memory handling | highest risk, highest memory pressure, biggest cost if scheduler/cache story is weaker than vLLM | interesting later experiment, not first move |

## Why `20b` First, Not `120b`

This was one of the key review questions.

The answer is not "because `120b` is bad." It is "because `20b` is the better first experiment."

## Reasons

- `20b` has much lower memory-risk and lower experiment blast radius.
- `20b` is currently the `fast` lane, which is the lane most likely to benefit from repeated-prefix interactive workflows.
- `20b` is the easiest place to prove whether pure-MLX cache/control wins are real on this stack.
- `120b` is the lane where giving up vLLM scheduler advantages is most expensive.

### Inference from local facts

This conclusion is an inference from:

- local artifact sizes
- current alias roles (`fast` vs `deep`)
- the documented differences between `vllm-metal` and pure-MLX-serving paths

It is not a benchmark result. That is important.

## Model-Family Research for `vLLM` / `vllm-metal`

This section captures the model-family research that directly informs the runtime decision.

## Strongest current fits

### GPT-OSS

Why it matters:

- native MXFP4 release
- post-trained around MXFP4
- strong quality-per-gig on Apple
- explicit vLLM recipe and optimization story

Primary sources:

- <https://openai.com/index/introducing-gpt-oss/>
- <https://huggingface.co/openai/gpt-oss-120b>
- <https://docs.vllm.ai/projects/recipes/en/latest/OpenAI/GPT-OSS.html>

### Qwen3-Coder-Next

Why it matters:

- strongest coding-agent-oriented non-GPT family found in the research
- explicit vLLM recipe
- explicit tool-calling parser expectations

Primary sources:

- <https://huggingface.co/Qwen/Qwen3-Coder-Next>
- <https://github.com/QwenLM/Qwen3-Coder>
- <https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Coder-480B-A35B.html>

Important caveat:

- this is still a Qwen-family direction, and Qwen3-Next is already the current pain point in local OpenCode usage

### Seed-OSS-36B

Why it matters:

- strong middleweight candidate
- dedicated `seed_oss` parser in current local vLLM capabilities
- official vLLM recipe exists

Primary sources:

- <https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Instruct/blob/main/MODEL_CARD.md>
- <https://docs.vllm.ai/projects/recipes/en/latest/Seed/Seed-OSS-36B.html>

## Plausible canaries

### GLM-4.5-Air / GLM-4.7

Why they matter:

- official cards explicitly mention vLLM parser/reasoner support
- good non-Qwen, non-GPT family to keep in view

Primary sources:

- <https://huggingface.co/zai-org/GLM-4.5-Air>
- <https://huggingface.co/zai-org/GLM-4.7-Flash>
- <https://docs.vllm.ai/en/latest/features/tool_calling/>

### Kimi-K2-Thinking

Why it matters:

- globally interesting for vLLM
- explicit recipe and throughput guidance

Why it is lower priority here:

- much less Apple-practical for the current local budget and runtime shape

Primary source:

- <https://docs.vllm.ai/projects/recipes/en/latest/moonshotai/Kimi-K2-Think.html>

## Constraints

These are the operative constraints that another reviewer should keep in mind.

### Technical constraints

- Studio team lanes `8100-8119` are `mlxctl`-managed and must stay that way.
- Experimental runtime work belongs on `8120-8139`.
- Current production Studio runtime is `vllm-metal`.
- The current lock posture is conservative.
- No assumption should be made that current deployment realizes the full vLLM concurrency/cache story.
- No assumption should be made that pure MLX equals maximum throughput without evidence.

### Product / operations constraints

- no blind production runtime swap
- no unnecessary disturbance to proven GPT-OSS lanes
- no new LAN exposure
- no secret-bearing docs
- no treating speculative research as canon without canary evidence

### Scope constraints

- this report is about Apple Studio runtime strategy
- Jetson Orin AGX is only relevant insofar as it is not directly part of an MLX runtime decision
- `main` model-family replacement is related context, but it is not the same decision as the GPT-OSS runtime question

## Non-Goals

- This report does not choose a final architecture by prose alone.
- This report does not authorize a production migration.
- This report does not claim that `mlx-openai-server` equals vLLM in scheduler sophistication.
- This report does not claim that `mlx_lm.server` is ready for team-lane promotion.
- This report does not recommend immediate removal of `vllm-metal`.

## Open Questions / What Needs Verification

This is the section another senior engineer should challenge directly.

- Does `mlx-openai-server` materially outperform `vllm-metal` for `gpt-oss-20b` on repeated-prefix coding workloads?
- How much of vLLM's theoretical scheduler advantage is actually being realized in the current locked runtime?
- Does `gpt-oss-120b` ever become a good pure-MLX candidate if the real workload is mostly single-user and repeated-prefix?
- Can `mlx-openai-server` preserve reliable tool behavior under OpenCode for GPT-OSS?
- If `vllm-metal` paged attention matures, does that erase most of the reason to pursue pure MLX?

## Ranked Recommendation

This is the current assistant recommendation, intended to be challenged if the associate has stronger contrary evidence.

1. Keep `gpt-oss-120b` on `vllm-metal`.
2. Keep `gpt-oss-20b` on `vllm-metal` in production.
3. Reconsider pure MLX only through a canary on `gpt-oss-20b`.
4. If pure MLX is revisited, use `mlx-openai-server` before bare `mlx_lm.server`.
5. Treat `main` model-family replacement as a separate track from the GPT-OSS runtime choice.

## Method and Limitations

This report is based on:

- read-only local repo inspection
- read-only local runtime inspection
- source-backed web research using current upstream docs and model cards

This report is not based on:

- fresh runtime mutation
- fresh canary benchmarking
- live runtime swaps

Important limitation:

- many conclusions about `mlx-openai-server` are evidence-backed but still inference-limited because current upstream docs do not publish a vLLM-equivalent scheduler/cache design document

## Source Appendix

## Local repo and system evidence

Canonical local files:

- [platform/ops/runtime-lock.json](/home/christopherbailey/homelab-llm/platform/ops/runtime-lock.json)
- [docs/foundation/mlx-registry.md](/home/christopherbailey/homelab-llm/docs/foundation/mlx-registry.md)
- [docs/INTEGRATIONS.md](/home/christopherbailey/homelab-llm/docs/INTEGRATIONS.md)
- [platform/ops/README.md](/home/christopherbailey/homelab-llm/platform/ops/README.md)
- [layer-inference/RUNBOOK.md](/home/christopherbailey/homelab-llm/layer-inference/RUNBOOK.md)
- [layer-inference/optillm-local/SERVICE_SPEC.md](/home/christopherbailey/homelab-llm/layer-inference/optillm-local/SERVICE_SPEC.md)
- [layer-inference/optillm-local/runtime/patches/mlx_lm/README.md](/home/christopherbailey/homelab-llm/layer-inference/optillm-local/runtime/patches/mlx_lm/README.md)
- [layer-gateway/litellm-orch/decision-log.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/decision-log.md)

Read-only commands used during research:

- `./platform/ops/scripts/mlxctl status --checks --json`
- `./platform/ops/scripts/mlxctl vllm-capabilities --json`
- `./platform/ops/scripts/mlxctl vllm-render --validate --json`
- `ssh studio 'sysctl -n hw.memsize && sysctl -n machdep.cpu.brand_string'`
- `ssh studio 'du -shL ...'`

No secrets are reproduced in this document.

## Web / primary-source evidence

### GPT-OSS / MXFP4

- <https://openai.com/index/introducing-gpt-oss/>
- <https://cdn.openai.com/pdf/419b6906-9da6-406c-a19d-1bb078ac7637/oai_gpt-oss_model_card.pdf>
- <https://huggingface.co/openai/gpt-oss-120b>

### vLLM / serving / prefix caching

- <https://docs.vllm.ai/en/stable/index.html>
- <https://docs.vllm.ai/en/stable/design/prefix_caching.html>
- <https://docs.vllm.ai/projects/llm-compressor/en/latest/experimental/mxfp4/>
- <https://docs.vllm.ai/projects/recipes/en/latest/OpenAI/GPT-OSS.html>
- <https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Coder-480B-A35B.html>
- <https://docs.vllm.ai/projects/recipes/en/latest/Seed/Seed-OSS-36B.html>
- <https://docs.vllm.ai/projects/recipes/en/latest/moonshotai/Kimi-K2-Think.html>
- <https://docs.vllm.ai/en/latest/features/tool_calling/>

### `vllm-metal`

- <https://github.com/vllm-project/vllm-metal>

### `mlx-openai-server`

- <https://github.com/cubist38/mlx-openai-server>
- <https://pypi.org/project/mlx-openai-server/>

### MLX / MLX-LM

- <https://github.com/ml-explore/mlx-lm>
- <https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html>
- <https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.nn.quantize.html>

### Model-family cards

- <https://huggingface.co/Qwen/Qwen3-Coder-Next>
- <https://github.com/QwenLM/Qwen3-Coder>
- <https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Instruct/blob/main/MODEL_CARD.md>
- <https://huggingface.co/zai-org/GLM-4.5-Air>
- <https://huggingface.co/zai-org/GLM-4.7-Flash>

