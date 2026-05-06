# V2 Planning Material: V1 Keepers

Not current runtime truth. These are candidate patterns worth carrying into V2 because V1 evidence treated them as stable, accepted, or durability-improving.

## Keep

- Single public gateway with narrow aliases and strong ownership boundaries. Evidence: `README.md` centers LiteLLM as “single client-facing model/API gateway”; `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md` keeps LiteLLM as “the public control plane.”

- Registry-driven runtime/gateway synchronization. Evidence: `docs/journal/2026-01-18-mlx-sync-gateway.md` and `docs/journal/2026-02-11-mlx-runtime-single-contract.md`.

- Boring LAN-first runtime topology for Mini↔Studio traffic. Evidence: `docs/foundation/topology.md` current LAN paths; `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md` explicitly reset canon to LAN-first.

- Shared GPT runtime with explicit acceptance gates, not ad hoc per-lane lore. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md` and `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`.

- Separate specialized-runtime plane. Evidence: `docs/foundation/runtime-planes.md` defines a private, narrow runtime plane; `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md` says the adapter is good enough for a future orchestration prototype.

- Native Open WebUI + SearXNG + `safe_web` search path, hardened at the UI layer. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md`, `docs/journal/2026-04-30-websearch-quality-hardening.md`, `docs/journal/2026-05-01-searxng-reliability-hardening.md`.

- Source-scoped retrieval ingest with redaction and rollback. Evidence: `docs/journal/2026-03-04-codex-history-pilot-ingest.md` used `--source codex_history_pilot`, redaction, and delete-by-source rollback.

- Managed OpenHands service with local bind and tailnet-only operator exposure. Evidence: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md` preserves `127.0.0.1:4031` and “no LAN exposure added.”

- Speech facade pattern: one live voice gateway in front of backend details. Evidence: `docs/foundation/topology.md` calls `voice-gateway` the approved LAN-visible speech facade; `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md` aligns docs to that live reality.

- Localhost-only monitoring and repo-managed deployed config. Evidence: `docs/journal/2026-02-09-prometheus-grafana-setup.md` keeps Prometheus/Grafana localhost-only and says repo configs remain source of truth.

- Append-only journal and narrow repo-root control surface. Evidence: `docs/journal/2026-02-08-journal-integrity-policy.md` and `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`.

- Worktree-first agent discipline for mutable work. Evidence: `AGENTS.md` and `docs/OPENCODE.md` both require linked worktrees for Build/Verify and keep the primary worktree as baseline-only.

## Keep With Caution

- Gateway cleanup hooks. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md` shows they can rescue a narrow contract. Caution: `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md` warns against letting LiteLLM become the general formatting owner.

- OptiLLM coding profiles. Evidence: `docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md` and `2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`. Caution: the evidence supports targeted profiles/canaries, not global defaults.

- Elastic retrieval backend. Evidence: `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md` made Elastic primary. Caution: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md` reminds that backend stability and answer-quality fitness are different questions.

## Needs Human/ChatGPT Review

- Whether “shared GPT runtime” should remain a V2 default architecture or just a transitional V1 success pattern.
- Whether “specialized runtime plane” should be launched in V2 immediately or held until orchestration needs are concrete.
- Whether OpenHands should stay in V2 scope at all if sandbox/runtime image management remains operationally heavy.
