# Constraints and Decisions

## Must
- LiteLLM is the single gateway for clients.
- No inference in TinyAgents (routing only).
- Use `uv`; do not mutate system Python.
- Do not touch existing services (Ollama, OpenVINO, MLX) without approval.
- Ports are immutable without a migration phase.

## Should
- Keep changes small and reversible.
- Prefer config-driven wiring; avoid hardcoded IPs/ports.
- Keep docs current with any topology change.

## Prohibited without approval
- Change/reuse existing ports.
- Expose new LAN-facing services.
- Bypass LiteLLM gateway.
- Store secrets in the repo or in prompts.

## Decisions (current)
- LiteLLM is the single gateway.
- Plain logical model names for clients.
- Open WebUI points to LiteLLM.
- OpenVINO runs as a standalone backend and is not currently wired as active LiteLLM handles.
- Ports treated as immutable.
