# Service Spec: Open WebUI

## Purpose
Human-facing UI for LLM interactions routed through LiteLLM.

## Interface
- HTTP UI: `127.0.0.1:3000` (localhost; access via Tailscale Serve)
- Health: `GET /health`

## Dependencies
- LiteLLM proxy at `http://127.0.0.1:4000/v1`

## Configuration
- `/etc/open-webui/env` (systemd EnvironmentFile)
- Data stored in `/home/christopherbailey/.open-webui`
