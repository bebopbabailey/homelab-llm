# V2 Planning Material: Host/Canon Reconciliation

Not current runtime truth. This file compares current Mini and Studio host inventories against authoritative repo canon before any runtime rebuild slice.

Canon precedence remains: [docs/_core/SOURCES_OF_TRUTH.md](../_core/SOURCES_OF_TRUTH.md). Host inventory is still required before mutation when canon and live reality diverge.

## How To Read This File

- Authoritative repo canon remains the formal source of truth for current contracts.
- Host inventory remains the required reality check before runtime rebuild on any touched surface.
- If an item is ambiguous, classify it conservatively and do not normalize it into V2 direction.

## Reconciliation Items

### Studio 8101 MLX lane contradiction

- Host: `Studio`
- Observed state: [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md) observed no `8101` listener, disabled `com.bebop.mlx-lane.8101`, and a host-local MLX registry showing `8100-8102` down/null.
- Repo/canon expectation: [../foundation/topology.md](../foundation/topology.md) and [../PLATFORM_DOSSIER.md](../PLATFORM_DOSSIER.md) still describe `192.168.1.72:8101` as the active MLX inference lane under `com.bebop.mlx-lane.8101`.
- Risk: high
- Proposed classification: `do not touch yet`
- Verification needed before action: human review of Studio repo checkout posture, `mlxctl` expectations, launchd labels, and whether canon or host drifted last.
- Blocks Phase 1A: `no`

### Mini shadow LiteLLM on 127.0.0.1:4001 with unknown path

- Host: `Mini`
- Observed state: [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md) observed a live shadow LiteLLM listener on `127.0.0.1:4001` tied to `homelab-llm-qwen-agent-shadow-20260415`, a path not shown in `git worktree list`.
- Repo/canon expectation: [../INTEGRATIONS.md](../INTEGRATIONS.md) still mentions `4001` only as an optional shadow validation path, while [V1_DO_NOT_REPEAT.md](V1_DO_NOT_REPEAT.md) and [REBUILD_CUTOVER_MAP.md](REBUILD_CUTOVER_MAP.md) treat stale shadow infrastructure as something that must not silently survive.
- Risk: high
- Proposed classification: `unknown`
- Verification needed before action: identify process ancestry, config source, callers, and whether any active Mini gateway or OpenHands path still depends on it.
- Blocks Phase 1A: `yes`

### Mini Prometheus exposure on *:9090

- Host: `Mini`
- Observed state: [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md) observed Prometheus listening on `*:9090`.
- Repo/canon expectation: [../foundation/topology.md](../foundation/topology.md), [../PLATFORM_DOSSIER.md](../PLATFORM_DOSSIER.md), and [../INTEGRATIONS.md](../INTEGRATIONS.md) all describe Prometheus as localhost-only on `127.0.0.1:9090`.
- Risk: medium
- Proposed classification: `rebuild clean`
- Verification needed before action: confirm whether any current dashboards, scrapers, or operators intentionally depend on non-local exposure before later cleanup.
- Blocks Phase 1A: `no`

### Mini Home Assistant tailnet mapping mismatch

- Host: `Mini`
- Observed state: [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md) observed Tailscale Serve mapping `themini.tailfd1400.ts.net:8123` to `192.168.1.40:8123`.
- Repo/canon expectation: [../foundation/topology.md](../foundation/topology.md) and [../PLATFORM_DOSSIER.md](../PLATFORM_DOSSIER.md) still describe Home Assistant on DietPi at `192.168.1.70:8123`.
- Risk: high
- Proposed classification: `unknown`
- Verification needed before action: owner confirmation of the actual Home Assistant host and whether the Tailscale serve target is stale, redirected, or the new live reality.
- Blocks Phase 1A: `no`

### Studio docs-mcp-main mismatch

- Host: `Studio`
- Observed state: [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md) observed `com.bebop.docs-mcp-main` running in launchd, but no `8013` listener.
- Repo/canon expectation: [../foundation/topology.md](../foundation/topology.md), [../PLATFORM_DOSSIER.md](../PLATFORM_DOSSIER.md), and [../../services/docs-mcp/SERVICE_SPEC.md](../../services/docs-mcp/SERVICE_SPEC.md) describe Docs MCP as a bearer-authenticated MCP facade on `192.168.1.72:8013/mcp`.
- Risk: medium
- Proposed classification: `unknown`
- Verification needed before action: inspect actual serve mode, expected bind behavior, and whether the service is healthy but non-listening, crashed after launch, or intentionally dormant.
- Blocks Phase 1A: `no`

### Studio llmster launchd/live-state mismatch

- Host: `Studio`
- Observed state: [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md) observed a live `llmster` process and `192.168.1.72:8126` listener while `launchctl print system/com.bebop.llmster-gpt.8126` reported `state = not running`.
- Repo/canon expectation: [../foundation/topology.md](../foundation/topology.md), [../PLATFORM_DOSSIER.md](../PLATFORM_DOSSIER.md), and [../../services/litellm-orch/SERVICE_SPEC.md](../../services/litellm-orch/SERVICE_SPEC.md) all treat `8126` as the active incumbent GPT compatibility surface under `com.bebop.llmster-gpt.8126`.
- Risk: high
- Proposed classification: `do not touch yet`
- Verification needed before action: reconcile whether launchd state, process ancestry, or plist posture is the trustworthy operational signal and whether the live public dependency is actually managed the way canon claims.
- Blocks Phase 1A: `yes`

### Studio pgvector and Kibana phase-one ambiguity

- Host: `Studio`
- Observed state: [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md) observed Postgres / pgvector on `55432` and Kibana on `5601`, both still present beside Elasticsearch plus memory API.
- Repo/canon expectation: [../../services/vector-db/SERVICE_SPEC.md](../../services/vector-db/SERVICE_SPEC.md) still keeps `legacy` rollback posture for pgvector and documents Kibana as localhost-only, while [V2_MIGRATION_NOTES.md](V2_MIGRATION_NOTES.md) and [V1_KEEPERS.md](V1_KEEPERS.md) treat Elastic plus memory API as the stronger retrieval incumbent.
- Risk: medium
- Proposed classification: `unknown`
- Verification needed before action: decide whether pgvector and Kibana are still operational dependencies, rollback-only surfaces, or stale carry-forward.
- Blocks Phase 1A: `no`

## Phase 1A Blocker Summary

- Mini shadow LiteLLM on `127.0.0.1:4001` is a Phase 1A blocker because it may represent an undocumented gateway dependency or stale shadow path still in use.
- Studio `8126` launchd/live-state mismatch is a Phase 1A blocker because the incumbent public GPT compatibility surface exists, but ownership and truth-path are unclear.

## Tracked But Non-Blocking For Phase 1A

- Studio `8101` MLX lane contradiction remains high risk, but MLX rebuild is explicitly out of scope for Phase 1A.
- Mini Prometheus exposure mismatch should be rebuilt clean later, but it does not prevent public gateway planning.
- Mini Home Assistant tailnet mapping mismatch is unrelated to the first public gateway slice.
- Studio Docs MCP mismatch and pgvector/Kibana ambiguity remain tracked for later retrieval/tooling review, not Phase 1A gating.
