# PLATFORM_CONSTRAINTS

## Must
- Routing-only; no inference in Tiny Agents.
- Use `uv` only; no system Python mutations.
- Do not touch existing services (Ollama, OpenVINO, MLX).
- Keep LiteLLM as the single gateway.
- No MCP until explicitly planned.
- Ports are immutable without a migration phase.

## Should
- Small, reversible changes; keep docs current.
- Config-driven; avoid hardcoding IPs/ports.
- Single source of truth for config.

## Non-goals
- No UI layer.
- No new inference backends.
- No new LAN-exposed services without approval.

## Prohibited without approval
- Change/reuse existing ports.
- Expose new LAN-facing services by default.
- Bypass LiteLLM gateway.
- Introduce MCP.
- Store secrets in repo or prompts.
