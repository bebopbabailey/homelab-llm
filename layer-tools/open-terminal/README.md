# Open Terminal

## Purpose
Provide a durable terminal-inspection surface on the Mini without changing the
current LiteLLM-centered model contract.

## Runtime shape
- Native API container for Open WebUI human UX: `127.0.0.1:8010`
- MCP container for localhost-only tooling: `127.0.0.1:8011/mcp`
- Both stay localhost-only

## First-slice scope
- Bind mount: `/home/christopherbailey/homelab-llm:/lab/homelab-llm:ro`
- Current live MCP path is the localhost-only direct backend on
  `127.0.0.1:8011/mcp`
- A shared LiteLLM MCP alias for a filtered read-only subset remains follow-on
  work
- The direct backend may expose more upstream tools, but that must not be
  mistaken for an approved shared LiteLLM surface

## Security posture
- No `docker.sock`
- No whole-host bind mounts
- No write mount for the repo
- No LAN exposure

## Validate
See `RUNBOOK.md`.
