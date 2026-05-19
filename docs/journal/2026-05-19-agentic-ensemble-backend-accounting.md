# 2026-05-19 - Agentic ensemble backend accounting

## Objective
Account for the `100 GB` general-capability ensemble from the Gemma 4 /
Qwen3.6 survey as a possible scaling substrate for agentic systems, while
separating greenfield fit from current Studio runtime reality.

This is a design/accounting entry only. No models were downloaded and no
runtime, LiteLLM, launchd, port, registry, or gateway changes were made.

## Decision
The stack is useful enough to reserve conceptually, but not stable enough to
promote as a public multi-model agent lane yet.

Use it as a staged backend substrate:

- Keep GPT-OSS 120B on the current `llmster` / llama.cpp path for broad
  reasoning, planning, synthesis, and general tool execution.
- Treat Gemma 4 31B as the general/multimodal specialist, but validate the
  artifact first because Gemma 4 quantization quality is materially
  artifact-dependent.
- Treat Qwen3.6 27B as the coding/agentic specialist, but validate parser,
  tool-call, and long-context behavior before using it as an automated coding
  worker.
- Keep LiteLLM as the only daily-use front door once any specialist is
  promoted. Direct backend calls remain diagnostic and promotion gates only.

The intended future shape is role routing, not a single omnibus model:

| Role | First candidate | Backend posture | Promotion read |
| --- | --- | --- | --- |
| `reasoning` / `planning` | GPT-OSS 120B MXFP4 GGUF | Already live on Studio `8126` through `llmster` | Stable enough for daily use through `deep` |
| `general` / multimodal | Gemma 4 31B 4-bit | New candidate backend, likely GGUF first for boring serving or PLE-safe MLX for Apple-quality validation | Useful, but not yet proven in this lab |
| `coding` / agentic | Qwen3.6 27B OptiQ 4-bit | New candidate backend, MLX preferred if `mlxctl` is repaired; GGUF fallback for llama.cpp/LM Studio | High value, but parser/tool reliability must gate promotion |

## Current reality
Live read-only checks on 2026-05-19 showed:

- Mini LiteLLM readiness is healthy and DB-backed auth is connected.
- Studio `llmster` is listening on `192.168.1.72:8126` and advertises
  `llmster-gpt-oss-20b-mxfp4-gguf` and
  `llmster-gpt-oss-120b-mxfp4-gguf`.
- Studio `lms ps --json` shows GPT-OSS 20B and 120B loaded/idle with
  `contextLength=32768`.
- Studio `8101` is not listening and is disabled in launchd.
- Studio `8100` and `8102` launchd labels are enabled but repeatedly exiting;
  their MLX GPT model paths are missing.
- Studio `mlxctl status --json` currently fails from the installed
  `/Users/thestudio/bin/mlxctl` because it resolves repo root incorrectly and
  looks for `/platform/registry/services.jsonl`.
- Studio MLX registry currently contains Qwen3-Coder-Next entries and stale
  `8123` serving metadata, but no live listener exists on `8123`.
- Studio has ample storage headroom: about `3.3 TiB` free.

Repo docs currently contain drift around the former Qwen `main` lane. Treat the
live checks plus current LiteLLM config as the operational baseline:
`deep`/`fast` on `8126` are real; public Qwen/MLX is not.

## Artifact accounting
The 100 GB team from `2026-05-11-gemma4-qwen36-artifact-fit.md` remains a
reasonable target if GPT-OSS 120B is reused from the live `llmster` store.

| Slot | Artifact | Availability | Approx weight | Local state |
| --- | --- | --- | ---: | --- |
| GPT | `ggml-org/gpt-oss-120b-GGUF` / LM Studio GPT-OSS 120B MXFP4 | Available and already staged locally | about 59 GiB | Present and live |
| Gemma | `FakeRockert543/gemma-4-31b-it-MLX-4bit` | Available, PLE-safe MLX 4-bit | about 19 GiB | Not present |
| Gemma fallback | `unsloth/gemma-4-31B-it-GGUF` or `lmstudio-community/gemma-4-31B-it-GGUF` Q4 class | Available, GGUF plus optional `mmproj` | about 17-19 GiB plus sidecar | Not present |
| Qwen | `mlx-community/Qwen3.6-27B-OptiQ-4bit` | Available, text-only MLX OptiQ | about 15.4 GiB | Not present |
| Qwen fallback | `bartowski/Qwen_Qwen3.6-27B-GGUF` Q4_K_M | Available, GGUF plus optional `mmproj` | about 16.3 GiB plus sidecar | Not present |

New download pressure for the first serious test is therefore roughly
`34-36 GiB`, not `100 GB`, if the live GPT-OSS 120B backend is reused.
Any download remains subject to the repo download gate and must be preceded by
a disk check and explicit approval.

## Agentic scaling fit
This ensemble should be accounted for as three backend roles behind a router,
not as three public user-facing model names.

Recommended layering:

1. Direct backend validation on Studio experimental ports `8120-8139`.
2. One backend-specific LiteLLM shadow alias per validated specialist.
3. Stable role aliases only after direct and shadow gates pass:
   `general`, `coding`, `reasoning`, and later `critic` or `vision` if the
   behavior justifies it.
4. Agent orchestration above LiteLLM, not inside backend services. TinyAgents,
   LangGraph/orchestration-cockpit, or future router services should select
   roles; LiteLLM should continue to own auth, model aliasing, retries, and
   metrics.

Minimum promotion gates before agent use:

- Direct backend smoke: plain chat, system-message adherence, 8K/32K context
  sanity, non-stream and stream behavior where applicable, and no listener
  crashes.
- Tool-call gate for coding role: `auto` and at least one constrained mode
  must return structured OpenAI-compatible `tool_calls` reliably.
- LiteLLM shadow gate: `/v1/models`, Chat Completions, timeout behavior,
  request parameter dropping, Prometheus labels, and clean failure behavior.
- Agent gate: an operator-only OpenHands or equivalent coding task must complete
  without direct backend bypass.
- Multimodal gate for Gemma: image/document/OCR tests must pass on the exact
  serving stack before claiming a multimodal role.

## Backend path recommendation
Use the existing stable service paths first:

- GPT-OSS remains on `services/llama-cpp-server` / `llmster` and LiteLLM
  `deep`.
- Qwen3.6 and Gemma 4 should start as isolated candidate backends, not edits to
  the live `deep`/`fast` service.
- If using MLX team lanes, repair `mlxctl` first and use `8100-8119` only
  through the registry/controller contract.
- If using GGUF/LM Studio or llama.cpp for first smoke, use experimental
  `8120-8139` and promote only after direct evidence.
- Do not expose new LAN ports or public aliases until the candidate has a
  rollback story and a journaled validation record.

Best near-term first slice:

1. Repair `mlxctl` installed-path/repo-root drift or explicitly choose a
   GGUF-only experimental path for this ensemble.
2. Download exactly one new specialist first, preferably Qwen3.6 27B OptiQ MLX
   if MLX governance is repaired, otherwise Qwen3.6 27B GGUF Q4_K_M.
3. Validate it as `coding` in isolation.
4. Add Gemma only after the coding specialist path is boring, because Gemma's
   value depends on multimodal acceptance tests and artifact choice.

## Conclusion
Account for the ensemble now, but reserve it as a staged specialist substrate
rather than a ready production stack.

The stable anchor is GPT-OSS 120B on `llmster` behind LiteLLM. The useful next
capability is a Qwen3.6 coding specialist. Gemma 4 31B is the broader
general/multimodal slot, but it should not be promoted until the exact artifact
and serving method are proven locally.
