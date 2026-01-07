# 08-CONSTRAINTS

Hard guardrails for future coding agents (Tiny Agents project). Evidence is drawn from platform docs and contracts.

## Hard constraints (must)
- Routing-only: do not implement inference in the Tiny Agents repo.
  Evidence: `/home/christopherbailey/litellm-orch/README.md`, `/home/christopherbailey/litellm-orch/DEV_CONTRACT.md`
- Use `uv` for dependency management; avoid global/system Python mutations.
  Evidence: `/home/christopherbailey/litellm-orch/DEV_CONTRACT.md`
- Do not touch or modify existing services like Ollama.
  Evidence: `/home/christopherbailey/litellm-orch/DEV_CONTRACT.md`
- Keep LiteLLM as the single gateway; do not call OpenVINO or MLX backends directly from new services.
  Evidence: `/home/christopherbailey/litellm-orch/ARCHITECTURE.md`, `/home/christopherbailey/litellm-orch/docs/tinyagents-integration.md`
- No MCP integration unless explicitly planned; MCP is not present here.
  Evidence: `/home/christopherbailey/litellm-orch/AGENTS.md`
- Do not change or reuse existing ports without an explicit port-migration task.
  Evidence: `02-PORTS_ENDPOINTS_REGISTRY.md`

## Soft constraints (should)
- Prefer small, reversible changes and keep docs current.
  Evidence: `/home/christopherbailey/litellm-orch/AGENT_PREFERENCES.md`
- Keep configuration declarative and environment-driven; avoid hardcoding IPs/ports in code.
  Evidence: `/home/christopherbailey/litellm-orch/DEV_CONTRACT.md`
- Maintain a single source of truth for config to avoid drift.
  Evidence: `/home/christopherbailey/litellm-orch/AGENT_PREFERENCES.md`

## Explicit non-goals for Tiny Agents
- No UI layer (Open WebUI remains the UI).
- No new inference backends; rely on existing MLX and OpenVINO services via LiteLLM.
- No new LAN-exposed services without explicit approval and documentation.

## Prohibited actions without approval
- Do not change or reuse existing ports (4000, 3000, 9000, 8100-8103, 8109, 11434) without a port-migration phase.
- Do not expose new LAN-facing services by default.
- Do not bypass LiteLLM as the gateway.
- Do not introduce MCP until explicitly planned.
- Do not store secrets in the repo or in prompts; use env files.
