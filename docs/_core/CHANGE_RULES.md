# Change Rules

Use these rules to keep documentation and registries consistent. Each rule is an explicit "if X changes, update Y" instruction.

## Consistency gate
After any change that affects runtime behavior (ports, bindings, auth, routing, handles/registries), validate the
high-risk claim families in `docs/_core/CONSISTENCY_DOD.md`.

If drift is discovered:
- record a claim entry in the dated audit ledger (`docs/_core/consistency_audit_2026-02.md` or current month), and
- fix now or disposition explicitly (fix_now / defer / accepted).

## Topology and Ports
- If any service port, host binding, or endpoint path changes, update:
  - `docs/foundation/topology.md`
  - `docs/PLATFORM_DOSSIER.md`
  - `TOPOLOGY.md`
  - Example: changing LiteLLM from 4000 to 4010 requires updating all three files.

- If a Tailscale Serve hostname, service-host mapping, or exposed operator URL changes, update:
  - `docs/PLATFORM_DOSSIER.md`
  - `docs/foundation/topology.md`
  - `TOPOLOGY.md`
  - `docs/INTEGRATIONS.md`
  - `docs/foundation/testing.md`
  - affected service `SERVICE_SPEC.md` / `RUNBOOK.md` / `CONSTRAINTS.md`
  - Example: moving OpenCode Web from a node-root hostname to `svc:codeagent` requires both runtime validation and doc updates across canon and the service bundle.

## Integrations and Routing
- If an integration is added/removed or routing logic changes, update:
  - `docs/INTEGRATIONS.md`
  - `docs/PLATFORM_DOSSIER.md`
  - Example: adding Open WebUI → LiteLLM routing or disabling OptiLLM requires updates in both docs.

## OpenCode control plane
- If repo-local OpenCode defaults, lane policy, agent names, skill names, or
  verification assumptions change, update:
  - `docs/OPENCODE.md`
  - `docs/INTEGRATIONS.md`
  - `docs/foundation/testing.md`
  - `docs/foundation/runtime-lock.md`
  - Example: changing the default OpenCode repo-work lane from `deep` to
    another handle requires both doc and verification-contract updates.

## Service Behavior and Contracts
- If a service's inputs, outputs, env vars, health checks, or lifecycle steps change, update:
  - That service's `layer-*/<service>/SERVICE_SPEC.md`
  - `docs/PLATFORM_DOSSIER.md`
  - Example: adding a required env var to `layer-gateway/optillm-proxy` must be reflected in its `SERVICE_SPEC.md` and the dossier.

## Registries (MLX, MCP, Handles)
- If model registry fields, sync behavior, or router/env generation changes, update:
  - `docs/foundation/mlx-registry.md`
  - `platform/registry/handles.jsonl` (if handles are affected)
  - `docs/PLATFORM_DOSSIER.md`
  - Example: adding a new registry field used by LiteLLM routing requires a doc update and any affected registry entries.

- If service identity, taxonomy, supported/experimental classification, or canonical service paths change, update:
  - `platform/registry/services.jsonl`
  - `scripts/service_registry.py`
  - `scripts/service_registry_audit.py`
  - `docs/foundation/service-catalog.md`
  - `docs/foundation/service-additions.md`
  - `docs/_core/SOURCES_OF_TRUTH.md`
  - Example: reclassifying `optillm-local` as an experiment requires registry, audit, and documentation updates together.

- If MCP server/tool metadata or schema changes, update:
  - `docs/foundation/mcp-registry.md`
  - `platform/ops/templates/mcp-registry.json`
  - `docs/foundation/tool-contracts.md`
  - Example: adding a new tool transport requires updating the registry template and tool contract notes.

## Studio Scheduling and Launchd Policy
- If Studio launchd managed labels, lane classifications, or scheduling policy behavior changes, update:
  - `docs/foundation/studio-scheduling-policy.md`
  - `docs/foundation/topology.md`
  - `docs/PLATFORM_DOSSIER.md`
  - Affected service `layer-*/<service>/SERVICE_SPEC.md` and `layer-*/<service>/RUNBOOK.md`
  - Example: adding a new owned Studio label under `com.bebop.*` requires policy-manifest, topology, dossier, and service-contract updates.

## Scripts and Validation
- If a validation script changes its inputs or assumptions, update:
  - `docs/foundation/testing.md`
  - `scripts/validate_handles.py` (implementation)
  - Example: adding a new handle validation rule should also add a corresponding test step in testing docs.

## Root Hygiene
- If the repo-root allowlist or root/journal/archive placement rules change, update:
  - `DOCS_CONTRACT.md`
  - `docs/_core/root_hygiene_manifest.json`
  - `scripts/repo_hygiene_audit.py`
  - `docs/foundation/testing.md`
  - `.github/workflows/repo-hygiene.yml`
  - `scripts/README.md`

## Internal Markdown Links
- If internal markdown links are added, removed, or retargeted, update:
  - `scripts/docs_link_audit.py`
  - `scripts/README.md`
  - `docs/foundation/testing.md`
  - `.github/workflows/repo-hygiene.yml`
  - affected docs/journal index entries or correction notes

## Control-Plane Sync
- If repo-local OpenCode behavior, skill aliases, or repo-hygiene validator
  contracts change, update:
  - `.codex/skills/homelab-durability/SKILL.md`
  - `docs/OPENCODE.md`
  - `docs/INTEGRATIONS.md`
  - `docs/foundation/testing.md`
  - `scripts/README.md`
  - `scripts/control_plane_sync_audit.py`
  - `.github/workflows/repo-hygiene.yml`

## Concurrent Efforts
- If local concurrent-effort rules, worktree preflight behavior, or effort
  metadata shape change, update:
  - `AGENTS.md`
  - `.codex/skills/homelab-durability/SKILL.md`
  - `docs/_core/CONCURRENT_EFFORTS.md`
  - `docs/OPENCODE.md`
  - `docs/foundation/testing.md`
  - `scripts/worktree_effort.py`
  - `scripts/start_effort.py`
  - `scripts/service_registry.py`
  - `scripts/service_registry_audit.py`
  - `scripts/submodule_pin_audit.py`
  - `scripts/closeout_effort.py`
  - `scripts/README.md`
  - `scripts/control_plane_sync_audit.py`
  - `scripts/tests/test_worktree_effort.py`
  - `scripts/tests/test_start_effort.py`
  - `scripts/tests/test_service_registry_audit.py`
  - `scripts/tests/test_submodule_pin_audit.py`
  - `scripts/tests/test_closeout_effort.py`
  - `scripts/tests/test_control_plane_sync_audit.py`

## Runtime Lock
- If locked Studio runtime args, LiteLLM resilience settings, MLX lane auth/memory defaults,
  or pinned `optillm` provenance change, update:
  - `docs/foundation/runtime-lock.md`
  - `platform/ops/runtime-lock.json`
  - `platform/ops/scripts/validate_runtime_lock.py`
  - `docs/PLATFORM_DOSSIER.md`
  - affected service `SERVICE_SPEC.md` / `RUNBOOK.md`

## Journal Integrity
- Journal entries are **append-only**. Do not move or delete entries from `docs/journal/`.
- If a correction is needed, add a **new** entry that references the original.
- Always update `docs/journal/index.md` when adding a new entry.
