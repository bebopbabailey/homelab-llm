# Service Spec: Open WebUI

## Purpose
Human-facing UI for LLM interactions routed through LiteLLM.

## Interface
- HTTP UI: `0.0.0.0:3000`
- Health: `GET /health`

## Dependencies
- LiteLLM proxy at `http://127.0.0.1:4000/v1`

## Configuration
- `/etc/open-webui/env` (systemd EnvironmentFile)
- Data stored in `/home/christopherbailey/.open-webui`
