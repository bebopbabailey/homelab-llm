# V2 Planning Material: V1 Do Not Repeat

Not current runtime truth. These are V1 traps, dead ends, or failure patterns that V2 should avoid unless new evidence clearly overturns them.

## Avoid

- Split boot/runtime authority. Evidence: `docs/journal/2026-02-11-mlx-runtime-single-contract.md` attributes drift on `8101` to “split authority.”

- Leaving rollout lanes half-retired. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md` found `8123` still running after it had already fallen out of the active alias surface.

- Treating tailnet transport as the core service contract when a stable LAN path exists. Evidence: `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md` explicitly supersedes the earlier tailnet-only contract from `2026-03-10`.

- Promoting Qwen/vLLM constrained-tool behavior without hard proof. Evidence: `docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md` ended `NO-GO`; `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md` later retired `main`.

- Assuming direct backend success means gateway success. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md` shows direct oMLX was fine while the LiteLLM alias degraded and failed.

- Reviving custom web-search glue too early. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md` says the stack was intentionally deleted instead of preserved; later hardening stayed on the native path.

- Confusing backend bring-up with retrieval-quality acceptance. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md` had “no gate-passing candidate” despite a working store; `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md` solved runtime substrate, not all evaluation questions.

- Assuming upstream MCP route support is production-ready because registration/listing works. Evidence: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md` proved the control-plane objects worked but the real MCP route still timed out or 500’d.

- Letting repo root become a dump of plans, review packs, and dated artifacts. Evidence: `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`.

- Treating experimental systems as defaults before stable acceptance. Evidence: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md` says the conservative status remained “not yet proven viable for promotion”; `docs/journal/2026-04-15-qwen3-coder-next-failure-closeout.md` explicitly abandoned that project; `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md` says “do not add an oMLX LiteLLM shadow alias yet.”

## Strong No-Go Decisions

- No public `main-shadow` promotion on V1’s `vllm-metal` path. Evidence: `docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md`.

- No shared LiteLLM-owned OpenTerminal MCP lane on the evaluated upstream baseline. Evidence: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`.

- No GPT MLX shadow service via the attempted LM Studio isolation method. Evidence: `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md` says the second server changed the incumbent global server instead of isolating it.

## Needs Human/ChatGPT Review
- Whether any V1 “do not repeat” item should be downgraded from a no-go to a re-test candidate because upstreams have moved since the journal entry.
- Whether V2 should retire some V1 terms entirely (`main`, shadow-port language, certain boost lanes) to reduce accidental carryover.
