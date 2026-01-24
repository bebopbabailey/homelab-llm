# Operating Model

This is a short navigation guide. Details live in the foundation docs:
- `docs/foundation/overview.md`
- `docs/foundation/topology.md`
- `docs/foundation/constraints-and-decisions.md`
- `docs/foundation/service-additions.md`
- `docs/foundation/testing.md`

## Stage Loop
Inventory → Constraints → Minimal contract → Wire → Validate → Codify → Prune

- Inventory: enumerate services, ports, and registries from `docs/PLATFORM_DOSSIER.md` and `docs/foundation/topology.md`.
- Constraints: apply non-negotiables from `docs/foundation/constraints-and-decisions.md`.
- Minimal contract: define the smallest viable `SERVICE_SPEC.md` and tool contracts; see `docs/foundation/service-additions.md` and `docs/foundation/tool-contracts.md`.
- Wire: connect routing and integrations; see `docs/INTEGRATIONS.md` and `docs/foundation/mlx-registry.md`.
- Validate: run smoke tests and checks from `docs/foundation/testing.md`.
- Codify: update canonical docs and registries in place; see `docs/PLATFORM_DOSSIER.md` and `docs/_core/CHANGE_RULES.md`.
- Prune: remove stale plans or deprecated notes; see `docs/archive` and `docs/deprecated`.

## Agent Modes
### Discover
- Read `docs/_core/SOURCES_OF_TRUTH.md` to locate canonical inputs.
- Confirm topology and ports in `docs/foundation/topology.md`.
- Check integrations in `docs/INTEGRATIONS.md`.

### Design
- Align with constraints in `docs/foundation/constraints-and-decisions.md`.
- Draft minimal contracts (`SERVICE_SPEC.md`, tool contracts).
- Identify required registry updates (MLX, MCP, handles).

### Build
- Implement only what the minimal contract requires.
- Keep routing and registry sync steps aligned with `docs/foundation/mlx-registry.md`.
- Avoid moving files; update docs in place per `docs/_core/CHANGE_RULES.md`.

### Verify
- Execute the verification steps in `docs/foundation/testing.md`.
- Re-check ports/endpoints against `docs/foundation/topology.md`.
- Confirm integrations reflect `docs/INTEGRATIONS.md`.
