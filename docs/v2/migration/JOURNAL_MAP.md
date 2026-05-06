# V2 Planning Material: Journal Map

Not current runtime truth. This file is migration seed material derived from V1 journals. Canonical current truth remains the active platform and service docs named in `docs/_core/SOURCES_OF_TRUTH.md`.

## Use
- Read by theme, not by chronology.
- Prefer the entries below when extracting durable lessons, accepted contracts, no-go calls, and reversions.

## Theme Map

### Gateway / LiteLLM / aliases
- `docs/journal/2026-01-18-mlx-sync-gateway.md` — MLX registry became the source of truth; gateway sync was derived from it.
- `docs/journal/2026-02-18-litellm-harmony-normalization.md` — GPT wire-format cleanup moved to LiteLLM guardrails.
- `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md` — `main` only accepted with narrow non-stream post-call cleanup.
- `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md` — `deep` moved to shared `8126` under usable-success gate.
- `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md` — `fast`/`deep` stabilized on shared `8126`; temporary aliases retired.
- `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md` — `8123-8125` retired.
- `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md` — Qwen `main` retired from production surface.

### Studio MLX / runtime lanes / control plane
- `docs/journal/2026-02-11-mlx-runtime-single-contract.md` — boot/runtime drift fixed by single registry contract.
- `docs/journal/2026-02-25-vllm-metal-8121-async-scheduler-root-cause.md` — async scheduler crash isolated; `--no-async-scheduling` became mitigation.
- `docs/journal/2026-02-27-gpt-oss-post117-reconciliation.md` — tuned overlap viability replaced stale blanket failure claims.
- `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md` — LAN-first Mini↔Studio contract superseded tailnet-only idea.

### vLLM-metal / MLX / oMLX / llama.cpp / llmster
- `docs/journal/2026-02-18-mlx-runtime-backend-loop-and-revert.md` — Omni/llama.cpp exploration reverted; per-port MLX stayed live.
- `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md` — `llmster` rollout gate defined.
- `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md` — `llmster` won the GPT `deep` cutover.
- `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md` — direct oMLX good; LiteLLM shadow alias degraded and failed.
- `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md` — narrow `omlx-runtime` adapter validated as specialized-runtime portal.

### OptiLLM / inference-time compute
- `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md` — entropy decoding remained unproven for promotion.
- `docs/journal/2026-02-22-optillm-mlx-server-diff-rebase-and-go.md` — strict GO was achieved only after patch maintainability was restored.
- `docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md` — coding-oriented `boost-*` aliases were added as controlled overlays.
- `docs/journal/2026-03-06-plansearchtrio-reasoning-effort-synthesis.md` — high reasoning effort paid off only in late synthesis/rewrite stages.

### OpenCode / Codex workflow
- `docs/OPENCODE.md` — repo-local control plane and worktree discipline.
- `docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md` — OpenCode defaults were tuned around explicit coding profiles.
- `docs/journal/2026-03-04-codex-history-pilot-ingest.md` — Codex history ingest used redaction-first, source-scoped rollback.
- `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md` — repo root narrowed to a high-trust search/control surface.

### OpenHands / sandboxing
- `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md` — OpenHands moved from manual session to managed service without LAN exposure.
- `docs/journal/2026-04-15-qwen-agent-proxy-openhands-shadow-slice.md` — direct sidecar path worked better than optional LiteLLM shadowing.
- `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md` — shared LiteLLM-owned MCP lane was upstream-blocked.

### Model selection: Qwen / GPT-OSS
- `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md` — Qwen was accepted only for a narrow contract.
- `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md` — Qwen lane later retired.
- `docs/journal/2026-04-27-gpt-oss-responses-followup-contract.md` — GPT-OSS Responses contract codified around `llmster`.

### Web search / SearXNG / Open WebUI
- `docs/journal/2026-03-07-websearch-supported-path-reset.md` — custom proxy/schema stack deleted; native OWUI+SearXNG restored.
- `docs/journal/2026-04-30-owui-querygen-prompt-policy.md` — durable query-generation policy moved to host-level config.
- `docs/journal/2026-04-30-websearch-quality-hardening.md` — retrieval hygiene added without reviving custom stack.
- `docs/journal/2026-05-01-searxng-reliability-hardening.md` — bounded fallback replaced brittle hard-fail behavior.

### Vector DB / memory / retrieval
- `docs/journal/2026-03-04-studio-main-vector-store-v1.md` — pgvector scaffold was initial plan, not final default.
- `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md` — provisional QG1 had no gate-passing candidate.
- `docs/journal/2026-03-04-codex-history-pilot-ingest.md` — source-scoped, redaction-first memory ingest succeeded.
- `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md` — Elastic became primary backend; pgvector demoted to rollback only.

### Orin voice / ASR / TTS
- `docs/journal/2026-03-12-voice-gateway-xtts-runtime-proof-recovery.md` — XTTS proof stopped at import/CUDA readiness; no synthesis claim.
- `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md` — live contract centered on `voice-gateway`, not XTTS wrapper experiments.

### Monitoring / ops / security
- `docs/journal/2026-02-09-prometheus-grafana-setup.md` — monitoring stayed localhost-only with repo-managed configs.
- `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md` — service-to-service traffic moved to boring LAN.
- `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md` — operator UX kept tailnet-only, local bind preserved.

### Documentation / process / source-of-truth discipline
- `docs/journal/2026-02-08-journal-integrity-policy.md` — journals are append-only.
- `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md` — root allowlist formalized.
- `docs/journal/2026-04-02-homelab-durability-eval-loop.md` — machine-checked manifest outranks memory for hygiene tasks.

## Needs Human/ChatGPT Review
- Whether V2 should inherit any OptiLLM coding profiles as defaults; V1 evidence shows canaries and targeted wins, not universal acceptance.
- Whether any part of the retired Qwen lane deserves preservation beyond historical reference.
- Whether V2 wants to preserve the exact LiteLLM cleanup shims or instead re-test upstream/runtime behavior from a cleaner baseline.
