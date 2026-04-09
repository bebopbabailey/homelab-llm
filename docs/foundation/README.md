# Foundation Docs

These documents are the durable, agent-focused reference for current platform
truth plus future service additions under each `layer-*` directory.

## Read Order
1. `AGENTS.md`
2. `docs/_core/README.md`
3. `docs/_core/SOURCES_OF_TRUTH.md`
4. `docs/PLATFORM_DOSSIER.md`
5. `docs/foundation/topology.md`
6. `docs/INTEGRATIONS.md`

## Contents
- `overview.md` — system architecture, data flow, and key roles.
- `topology.md` — authoritative ports/endpoints and host mapping.
- `constraints-and-decisions.md` — guardrails and non-negotiable decisions.
- `service-additions.md` — step-by-step process for adding services/backends.
- `testing.md` — verification steps and smoke tests.
- `node-toolchain.md` — Node/Volta global CLI policy for agent hosts.
- `mlx-registry.md` — MLX registry and controller overview.
- `mcp-registry.md` — MCP registry template and schema.
- `tool-contracts.md` — tool input/output contracts.

## Sources Of Truth
- `docs/PLATFORM_DOSSIER.md`
- `docs/foundation/topology.md`
- `docs/foundation/constraints-and-decisions.md`
- `docs/INTEGRATIONS.md`
- `docs/OPENCODE.md`
- `layer-*/<service>/SERVICE_SPEC.md`

## Agent Expectations
- Repo-root descent rules live in root `AGENTS.md` and `docs/_core/README.md`.
- Update `NOW.md` when the active work changes.
- Prefer small, reversible changes.
- Keep docs current; avoid backlog drift.
- Keep a single source of truth where possible.
