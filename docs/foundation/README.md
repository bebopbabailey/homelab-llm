# Foundation Docs (for future service additions)

These documents are the durable, agent-focused reference for extending this repo
with new services under `/services`. They summarize the current topology, routing,
and constraints so new work stays compatible with the existing platform.

## Contents
- `overview.md` — system architecture, data flow, and key roles.
- `topology.md` — authoritative ports/endpoints and host mapping.
- `service-additions.md` — step-by-step process for adding services/backends.
- `constraints-and-decisions.md` — guardrails and non-negotiable decisions.
- `mcp-tools.md` — MCP tool usage and adoption guidance.
- `mcp-101.md` — analogy and system fit for MCP + tools.
- `mcp-registry.md` — MCP registry template and schema.
- `mlx-registry.md` — MLX registry and controller overview.
- `testing.md` — verification steps and smoke tests.

## Sources of Truth
- `docs/PLATFORM_DOSSIER.md` — current topology, ports, inventory, exposure.
- `docs/foundation/topology.md` — authoritative port map for this repo.
- `docs/foundation/constraints-and-decisions.md` — immutable constraints.
- `docs/INTEGRATIONS.md` — LiteLLM routing + Open WebUI/OpenVINO/OptiLLM linkage.
- `services/*/SERVICE_SPEC.md` — per-service runtime contract and env locations.
- `services/litellm-orch/ARCHITECTURE.md` and `services/ov-llm-server/ARCHITECTURE.md`
  — layered architecture framing.
- `services/*/SERVICE_SPEC.md` — per-service contract details.

## Agent Expectations (global)
- Update `TASKS.md` and service `AGENTS.md` before implementing new features.
- Prefer small, reversible changes; ask before large refactors.
- Keep docs current; avoid backlog drift.
- List non-negotiables early (stack, tools, services not to touch).
- Do not change global/system settings unless requested.
- Favor simple, deterministic naming and file layout.
- Put evolving details in metadata or config, not filenames.
- State test expectations explicitly, even if no tests exist.
- When unsure, ask before adding new test frameworks.
- Keep a single source of truth (env vars + one registry file).
- Avoid duplicate or conflicting configuration sources.

## MCP Adoption Checklist (planned)
- Define the MCP server (stdio vs HTTP/SSE) and where it runs.
- Document tool contracts and versions.
- Add server to the MCP tool registry and include health checks.
- Keep tool calls separate from LiteLLM model calls.
