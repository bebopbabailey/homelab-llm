# V2 Planning Material: Phase 1A Public Gateway Scope

Not current runtime truth. This file defines the first actual rebuild planning slice for the public gateway only. It is planning scope, not execution.

## Objective

- Define the first runtime rebuild slice around the public gateway contract only.
- Preserve current stable public alias behavior while planning additive V2 alias vocabulary.
- Avoid coupling Phase 1A to MLX rebuild, retrieval rebuild, speech rollout, host expansion, or broader runtime cleanup.

## Allowed Files And Services For Future Implementation

### Planning and canon docs

- `docs/v2/`
- `docs/INTEGRATIONS.md`
- `docs/foundation/topology.md`
- `docs/PLATFORM_DOSSIER.md`
- `docs/foundation/testing.md`

### Gateway service surfaces

- `services/litellm-orch/SERVICE_SPEC.md`
- `services/litellm-orch/RUNBOOK.md`
- `services/litellm-orch/CONSTRAINTS.md`
- `services/litellm-orch/config/router.yaml`
- existing tests under `services/litellm-orch/tests/`

### Read-only reference surfaces only

- `services/open-webui/SERVICE_SPEC.md`
- `services/voice-gateway/SERVICE_SPEC.md`
- `services/vector-db/SERVICE_SPEC.md`
- `services/docs-mcp/SERVICE_SPEC.md`

## Forbidden Files And Services

- systemd files
- launchd files
- env files and secret files
- Docker files
- `platform/registry/*`
- model registries
- deployment files
- Studio MLX control/config surfaces
- `services/vector-db` runtime mutation
- `services/docs-mcp` runtime mutation
- `services/openhands` implementation changes
- Orin and HP service/config work
- direct runtime/service reconfiguration on Mini or Studio

## Preconditions

- Continue using the existing linked worktree `/home/christopherbailey/homelab-llm-v2-cutover-map`. Do not create a second overlapping `docs/v2` lane.
- Resolve these Phase 1A blockers before runtime mutation:
  - Mini shadow LiteLLM on `127.0.0.1:4001`
  - Studio `8126` launchd/live-state mismatch
- Do not change ports, binds, or service managers in Phase 1A.
- Do not treat direct backend success as sufficient evidence for public gateway cutover.

## Acceptance Criteria

- The V2 gateway contract doc preserves current stable aliases and names additive V2 alias targets.
- The host/canon reconciliation doc classifies all required mismatches and states whether each blocks Phase 1A.
- The Phase 1A scope doc names exact allowed and forbidden surfaces.
- No new V2 doc makes a backend implementation name into architecture identity.
- No stable alias is removed or renamed in planning language.
- `voice-stt` and `voice-tts` remain future placeholders only, not Phase 1A live requirements.
- `/v1/responses` may remain a desirable compatibility target, but is not required as a mandatory Phase 1A runtime gate unless direct client dependency is confirmed.

## Verification Commands And Checks

### Docs-only checks for the planning pass

- `uv run python scripts/repo_hygiene_audit.py --json`
- `uv run python scripts/control_plane_sync_audit.py --strict --json`
- `uv run python scripts/service_registry_audit.py --strict --json`
- `uv run python scripts/docs_link_audit.py`

### Future gateway runtime checks to define, not run in this planning pass

- authenticated `GET /v1/models`
- authenticated `GET /v1/model/info`
- one smoke for `fast`
- one smoke for `deep`
- one smoke for additive `default` only if introduced in that slice
- one smoke for `code-main` only if introduced in that slice

Phase 1A should not require live smoke gates for:

- `voice-stt`
- `voice-tts`
- `/v1/responses`

unless a later implementation slice proves a direct dependency that must be kept live immediately.

## Rollback Expectations

- Planning-only rollback is docs-only.
- Future Phase 1A implementation rollback should be alias-map-first, then docs rollback.
- Rollback should not depend on MLX runtime churn, specialized-runtime cutover, or retrieval backend change.

## Unresolved Blockers

### Blocks Phase 1A

- Mini shadow LiteLLM on `127.0.0.1:4001`
- Studio `8126` launchd/live-state mismatch

### Tracked but non-blocking for Phase 1A

- Studio `8101` MLX lane contradiction
- Studio Docs MCP mismatch
- Mini Prometheus exposure mismatch
- Mini Home Assistant tailnet mapping mismatch
- Studio pgvector/Kibana ambiguity
