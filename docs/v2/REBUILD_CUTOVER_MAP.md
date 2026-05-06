# V2 Planning Material: Rebuild Cutover Map

Not current runtime truth. This is a planning map for preserve, rebuild, archive, and later-retirement decisions derived from current V2 doctrine and the Mini/Studio baseline inventories.

Primary evidence:

- [docs/v2/inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- [docs/v2/inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- [docs/v2/adr/](adr/)

## Preserve

### Mini public chat and search surface

- Host: `Mini`
- Current evidence/source: `open-webui.service`, current public gateway surface, and `searxng.service` are live in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: preserve in place during planning; treat as incumbent public contract evidence
- Reason: aligns with ADR 0001 and ADR 0005 while V2 rebuild decisions are still open
- Risk: medium; current implementation may carry V1 drift, but the client-facing contract still matters
- Verification needed before action: confirm exact public dependencies and auth boundaries before any cutover work

### Studio incumbent GPT/GGUF compatibility runtime

- Host: `Studio`
- Current evidence/source: live `8126` listener and process in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: preserve as incumbent compatibility evidence, not V2 identity
- Reason: supports fallback continuity without freezing V2 doctrine around a V1 product name
- Risk: medium; launchd state mismatch needs review before later cutover
- Verification needed before action: reconcile launchd state vs live process ownership

### Studio Elastic plus memory API retrieval path

- Host: `Studio`
- Current evidence/source: healthy `9200` and `55440` in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: preserve as incumbent retrieval runtime
- Reason: strongest current retrieval evidence, consistent with ADR 0006
- Risk: low to medium; quality still needs revalidation even if runtime is healthy
- Verification needed before action: run slimmer V2 retrieval eval gate before declaring default

### Studio model stores

- Host: `Studio`
- Current evidence/source: `~/.lmstudio`, `~/models`, `~/.cache/huggingface` in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: preserve
- Reason: model assets are expensive to reconstruct and encode both GGUF and MLX runtime history
- Risk: low
- Verification needed before action: inventory exact models needed for phase-one rebuild candidates

## Rebuild clean

### V2 command-center docs

- Host: `cross-host docs`
- Current evidence/source: V2 planning doctrine and inventories in [README.md](README.md), [inventory/HOST_INVENTORY_SUMMARY.md](inventory/HOST_INVENTORY_SUMMARY.md), and [adr/](adr/)
- Proposed V2 action: rebuild clean as the planning entrypoint now
- Reason: V2 lacked a stable top-level entrypoint before this pass
- Risk: low
- Verification needed before action: docs-only hygiene checks

### Public gateway implementation

- Host: `Mini`
- Current evidence/source: current gateway is live on Mini in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md); doctrine is in [adr/0001-one-public-gateway.md](adr/0001-one-public-gateway.md) and [adr/0003-registry-derived-routing.md](adr/0003-registry-derived-routing.md)
- Proposed V2 action: rebuild clean later behind the same public contract
- Reason: V2 doctrine says contract first; current implementation name and glue should not define the rebuild
- Risk: high if attempted before dependency mapping
- Verification needed before action: enumerate current clients, aliases, and upstream runtime dependencies

### Monitoring posture

- Host: `Mini`
- Current evidence/source: Prometheus is live on `*:9090` in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md), which conflicts with the keeper doctrine in [V1_KEEPERS.md](V1_KEEPERS.md)
- Proposed V2 action: rebuild clean later to match localhost-only doctrine
- Reason: preserve observability but remove drift from the rebuilt baseline
- Risk: medium
- Verification needed before action: identify dashboards, scrape dependencies, and any intentional exposure

### MLX lane surface

- Host: `Studio`
- Current evidence/source: repo canon says `8101` active, but host inventory shows it absent in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: rebuild clean only after host/canon reconciliation
- Reason: current evidence is contradictory
- Risk: high
- Verification needed before action: human review plus direct host reconciliation of registry, launchd labels, and repo checkout expectations

## Archive

### V1 shadow vocabulary and alias-era posture

- Host: `cross-host docs`
- Current evidence/source: [V1_DO_NOT_REPEAT.md](V1_DO_NOT_REPEAT.md) and [V1_KEEPERS.md](V1_KEEPERS.md)
- Proposed V2 action: archive conceptually; keep only as historical evidence
- Reason: V2 should not carry `main`, `main-shadow`, `boost-*`, or `shared-8126` as architecture vocabulary
- Risk: low
- Verification needed before action: ensure future docs use generalized doctrine language

### Mini OpenVINO and Ollama dead-end posture

- Host: `Mini`
- Current evidence/source: inactive `ollama.service` and crash-looping `ov-server.service` in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: archive as historical reference, not phase-one rebuild target
- Reason: no stable baseline evidence and no V2 doctrine support
- Risk: low
- Verification needed before action: none beyond confirming no active dependency emerges later

## Stop later

### Mini orchestration cockpit prototypes

- Host: `Mini`
- Current evidence/source: `orchestration-cockpit-graph.service` and `orchestration-cockpit-ui.service` are active but disabled in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: stop later after confirming no active operator dependency
- Reason: prototype plane, not phase-one boring baseline
- Risk: medium
- Verification needed before action: human confirmation that nothing relies on ports `2024` or `3030`

### Mini failed Qwen shadow sidecar

- Host: `Mini`
- Current evidence/source: `qwen-agent-proxy.service` is failed and disabled in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: stop later if any residual process or docs surface remains
- Reason: fits ADR 0007 retirement doctrine
- Risk: low
- Verification needed before action: confirm no dependent tailscale serve, unit alias, or wrapper remains

### Studio disabled shadow and legacy labels

- Host: `Studio`
- Current evidence/source: disabled shadow labels and disabled non-core MLX/OptiLLM labels in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: keep stopped now; formally retire later during cleanup
- Reason: they already fit the retired posture
- Risk: low
- Verification needed before action: ensure no generated docs or launchd sync expects them

## Delete later

### Mini stray shadow LiteLLM path

- Host: `Mini`
- Current evidence/source: live shadow LiteLLM on `127.0.0.1:4001` tied to a path not shown in `git worktree list` in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: delete later only after ownership and dependency review
- Reason: strong candidate for stale shadow residue, but not safe to assume
- Risk: high
- Verification needed before action: identify process ancestry, config source, and any callers

### Studio stale phase-one-disabled labels if later proven unused

- Host: `Studio`
- Current evidence/source: disabled labels listed in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: delete later only after a dedicated cleanup slice
- Reason: likely dead weight, but current pass is planning only
- Risk: medium
- Verification needed before action: host-owner review plus launchd policy audit

## Unknown / needs review

### Mini Prometheus exposure mismatch

- Host: `Mini`
- Current evidence/source: `*:9090` listener in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: unknown until intent is reviewed
- Reason: conflicts with expected localhost-only posture
- Risk: high
- Verification needed before action: determine whether exposure is intentional, proxied, or accidental drift

### Mini Home Assistant tailnet mapping mismatch

- Host: `Mini`
- Current evidence/source: Tailscale Serve maps `:8123` to `192.168.1.40:8123`, conflicting with repo references to `192.168.1.70:8123` in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: unknown until human review
- Reason: host reality and docs disagree
- Risk: high
- Verification needed before action: identify actual Home Assistant host and update canon later

### Studio `8101` MLX lane contradiction

- Host: `Studio`
- Current evidence/source: repo canon vs host inventory mismatch in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: unknown until reconciled
- Reason: cannot rebuild or retire safely from contradictory evidence
- Risk: high
- Verification needed before action: direct human review of Studio checkout, registry, and launchd posture

### Studio Docs MCP live-state contradiction

- Host: `Studio`
- Current evidence/source: running launchd job but no `8013` listener in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: unknown until reviewed
- Reason: process presence does not prove serving readiness
- Risk: medium
- Verification needed before action: inspect actual service mode and expected bind behavior

## Do not touch yet

### LiteLLM implementation stack

- Host: `Mini`
- Current evidence/source: current public gateway implementation is live in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- Proposed V2 action: do not touch yet
- Reason: V2 doctrine keeps the contract but this planning phase explicitly does not start a LiteLLM rebuild
- Risk: high if changed early
- Verification needed before action: later gateway-design slice with dependency inventory

### MLX runtime rebuild

- Host: `Studio`
- Current evidence/source: MLX state is contradictory in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: do not touch yet
- Reason: no stable baseline to rebuild from yet
- Risk: high
- Verification needed before action: host/canon reconciliation

### OpenHands expansion

- Host: `Mini`
- Current evidence/source: OpenHands is live in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md), but V2 doctrine keeps it conditional in [V2_MIGRATION_NOTES.md](V2_MIGRATION_NOTES.md)
- Proposed V2 action: do not touch yet
- Reason: phase-one scope excludes expansion
- Risk: medium
- Verification needed before action: decide whether it belongs in V2 at all before expanding it

### Orin and HP host integration work

- Host: `Orin`, `HP`
- Current evidence/source: pending inventory docs [inventory/ORIN_BASELINE_PENDING.md](inventory/ORIN_BASELINE_PENDING.md) and [inventory/HP_BASELINE_PENDING.md](inventory/HP_BASELINE_PENDING.md)
- Proposed V2 action: do not touch yet
- Reason: no baseline evidence exists in this planning slice
- Risk: medium
- Verification needed before action: complete host inventories first

## Phase-one rebuild candidates

### V2 command-center and doctrine surface

- Host: `cross-host docs`
- Current evidence/source: this V2 planning set plus [adr/](adr/)
- Proposed V2 action: phase-one rebuild candidate now
- Reason: planning entrypoint must exist before runtime rebuild slices
- Risk: low
- Verification needed before action: docs-only hygiene checks

### Public gateway contract map

- Host: `Mini` to `Studio`
- Current evidence/source: Mini public surfaces plus Studio incumbent runtime evidence in [inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md) and [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- Proposed V2 action: phase-one planning candidate
- Reason: clarifies what the boring contract actually needs to preserve before implementation changes
- Risk: medium
- Verification needed before action: list current consumers and backend dependencies

### Retrieval discipline gate

- Host: `Studio` with Mini clients
- Current evidence/source: incumbent Elastic + memory API in [inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md) and doctrine in [adr/0006-retrieval-discipline-before-backend-default.md](adr/0006-retrieval-discipline-before-backend-default.md)
- Proposed V2 action: phase-one planning candidate
- Reason: backend exists, but quality gate still needs to be defined
- Risk: medium
- Verification needed before action: assemble V2 eval pack and acceptance criteria

### Host/canon reconciliation slice

- Host: `Mini` and `Studio`
- Current evidence/source: major mismatches listed in [inventory/HOST_INVENTORY_SUMMARY.md](inventory/HOST_INVENTORY_SUMMARY.md)
- Proposed V2 action: phase-one planning candidate
- Reason: rebuild work should not proceed while core inventory contradictions remain unresolved
- Risk: low to medium
- Verification needed before action: targeted human review of the listed unknowns
