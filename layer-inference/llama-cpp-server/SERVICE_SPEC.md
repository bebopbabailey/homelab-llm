# Service Spec: llama-cpp-server

## Purpose
Provide the repo-owned GPT serving boundary for canonical `fast` / `deep`
serving using `llmster` with llama.cpp architecture behind it.

## Status
- Approved implementation boundary.
- `fast` is live on `8126` as part of the canonical shared GPT runtime stack.
- `deep` is now live on shared `8126` under the usable-success contract.
- The old MLX GPT rollback lanes on `8100` and `8102` are retired and unloaded.
- Public client contract remains LiteLLM-first.

## Host & Runtime
- Host: Mac Studio
- Runtime family: `llmster` headless daemon / LM Studio server
- Inference engine: llama.cpp architecture
- Intended bind: `192.168.1.72:8126`
- Intended launchd label: `com.bebop.llmster-gpt.8126`

## Logical lanes served
- `fast` -> `llmster-gpt-oss-20b-mxfp4-gguf`
- `deep` -> `llmster-gpt-oss-120b-mxfp4-gguf`

One shared `llmster` listener is the approved first shape because the official
LM Studio headless docs support OpenAI-compatible serving plus loaded model
identifiers on one server. If measured dual-load posture fails, `deep` may move
to a separate public Studio port in a later slice.

## Artifact policy
- Canonical GPT artifacts for this boundary are MXFP4 GGUF variants only.
- Public service path uses `llmster`.
- Raw `llama-server` mirrors stay in scope as truth-path validation and tuning
  infrastructure, but they are diagnostic-first and not the public promotion
  oracle by themselves.
- Studio storage policy for GPT rollout is `active runtime models + one staged
  next artifact`; with the GPT migration complete, stale rollback weights and
  duplicate caches are deleted and only active runtime artifacts remain.

## Client surface
- Direct backend surface: OpenAI-compatible `/v1/*`
- Repo client surface: LiteLLM aliases only
- No direct user/client routing to Studio GPT lanes

## Required runtime posture
- authentication enabled
- LAN serving enabled only for the approved Studio listener
- JIT loading disabled
- auto-evict disabled
- explicit loaded identifiers
- stable model residency with explicit `lms load`
- no TTL-based auto-unload for canonical lanes
- intended loaded set visible in both `lms ps --json` and `/v1/models`
- per-request MCP disabled
- `mcp.json` calling disabled
- no repetition penalties for GPT-OSS
- raw standalone launchers must use `--jinja`

## Acceptance criteria
- plain chat correctness
- structured simple output
- structured nested output
- non-stream auto tool use
- at least one strong constrained tool mode (`required` or named-tool forcing)
- concurrency / parallel serving behavior
- OpenAI-compatible serving behavior
- `/v1/responses` remains advisory for this slice unless it exposes a defect
  that also matters to the public Chat Completions lane
- large-schema tool integrity remains a diagnostic and tuning seam, not a hard
  promotion gate by itself unless it reproduces a public-lane defect
- public `deep` cutover was preceded by:
  - raw diagnostic validation
  - direct `llmster` validation
  - temporary Mini-side canary validation (now retired)
  - actual shared-posture proof on shared `8126`
- current locked `deep` result on shared `8126`:
  - plain chat `5/5`
  - structured simple `5/5`
  - structured nested `5/5`
  - auto noop `10/10`
  - auto arg-bearing `10/10`
  - `required` arg-bearing `9/10`
  - named forced-tool choice unsupported on the current backend path

## Non-goals
- MAIN replacement
- automatic `code-reasoning` replacement
- premature speculative/MTP tuning
