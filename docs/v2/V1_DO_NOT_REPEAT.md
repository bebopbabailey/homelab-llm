# V2 Planning Material: V1 Do Not Repeat

Not current runtime truth. These are V1 traps, dead ends, or failure patterns that V2 should avoid unless new evidence clearly overturns them.

## Permanent Rules

- Do not split boot/runtime authority. Evidence: `docs/journal/2026-02-11-mlx-runtime-single-contract.md`
- Do not leave shadow or rollout infrastructure half-retired. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`
- Do not treat tailnet transport as the core runtime contract when a stable LAN path exists. Evidence: `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`
- Do not assume direct backend success implies gateway success. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`
- Do not revive custom web-search glue by default. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md`
- Do not confuse backend bring-up with retrieval-quality acceptance. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`
- Do not treat raw mirrors as automatic promotion oracles. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md`, `docs/INTEGRATIONS.md`
- Do not promote experimental systems to defaults before stable acceptance. Evidence: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `docs/journal/2026-04-15-qwen3-coder-next-failure-closeout.md`, `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`
- Do not make LiteLLM the permanent owner of provider formatting when the backend should own it. Evidence: `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md`
- Do not let repo root compete with canon. Evidence: `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`

## Re-Test Only If Upstream or Runtime Conditions Materially Change

- Qwen/vLLM constrained-tool behavior. Evidence: `docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md`, `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`
- LiteLLM-owned upstream MCP route and session support. Evidence: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`
- Public oMLX aliasing through LiteLLM. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`
- The specific GPT MLX shadow-service isolation method rejected in April 2026. Evidence: `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`
- Narrow gateway cleanup shims that existed only to patch V1 backend defects. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md`

## V1 Vocabulary Not Worth Carrying Forward

- `main`
- `main-shadow`
- Shadow-port numbers such as `8123-8125`
- `boost-*`
- `shared-8126` as a product-identity term
- Temporary rollout labels that describe cutover posture rather than durable behavior

Evidence: `docs/INTEGRATIONS.md`, `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`, `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`, `docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md`

## Needs Human/ChatGPT Review

- Whether any current re-test candidate should be downgraded to permanent no-go because the surrounding architecture has moved too far for retest to be worthwhile.
