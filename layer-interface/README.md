# Interface Layer

Mission: human-facing clients and UI surfaces, including Mini-hosted UIs and
the Orin-hosted speech facade.

Current service boundaries in this layer:
- `open-webui`
- `grafana`
- `opencode-web`
- `voice-gateway`

This layer should only talk to LiteLLM for LLM traffic and must not call
inference backends directly.

See root docs: `/home/christopherbailey/homelab-llm/SYSTEM_OVERVIEW.md`.
