# Change Rules

Use these rules to keep documentation and registries consistent. Each rule is an explicit "if X changes, update Y" instruction.

## Topology and Ports
- If any service port, host binding, or endpoint path changes, update:
  - `docs/foundation/topology.md`
  - `docs/PLATFORM_DOSSIER.md`
  - `TOPOLOGY.md`
  - Example: changing LiteLLM from 4000 to 4010 requires updating all three files.

## Integrations and Routing
- If an integration is added/removed or routing logic changes, update:
  - `docs/INTEGRATIONS.md`
  - `docs/PLATFORM_DOSSIER.md`
  - Example: adding Open WebUI → LiteLLM routing or disabling OptiLLM requires updates in both docs.

## Service Behavior and Contracts
- If a service's inputs, outputs, env vars, health checks, or lifecycle steps change, update:
  - That service's `layer-*/<service>/SERVICE_SPEC.md`
  - `docs/PLATFORM_DOSSIER.md`
  - Example: adding a required env var to `layer-gateway/optillm-proxy` must be reflected in its `SERVICE_SPEC.md` and the dossier.

## Registries (MLX, MCP, Handles)
- If model registry fields, sync behavior, or router/env generation changes, update:
  - `docs/foundation/mlx-registry.md`
  - `layer-gateway/registry/handles.jsonl` (if handles are affected)
  - `docs/PLATFORM_DOSSIER.md`
  - Example: adding a new registry field used by LiteLLM routing requires a doc update and any affected registry entries.

- If MCP server/tool metadata or schema changes, update:
  - `docs/foundation/mcp-registry.md`
  - `platform/ops/templates/mcp-registry.json`
  - `docs/foundation/tool-contracts.md`
  - Example: adding a new tool transport requires updating the registry template and tool contract notes.

## Scripts and Validation
- If a validation script changes its inputs or assumptions, update:
  - `docs/foundation/testing.md`
  - `scripts/validate_handles.py` (implementation)
  - Example: adding a new handle validation rule should also add a corresponding test step in testing docs.

## Journal Integrity
- Journal entries are **append-only**. Do not move or delete entries from `docs/journal/`.
- If a correction is needed, add a **new** entry that references the original.
- Always update `docs/journal/index.md` when adding a new entry.
