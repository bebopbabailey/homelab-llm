# Interface Layer

Mission: human-facing clients and UI surfaces, including Mini-hosted UIs and
the Orin-hosted speech facade.

Live service roots formerly in this layer now live under `services/`:
- `services/open-webui`
- `services/grafana`
- `services/opencode-web`
- `services/voice-gateway`

This layer directory remains as transitional taxonomy and layer-level guidance
during the migration.

This layer should only talk to LiteLLM for LLM traffic and must not call
inference backends directly.

See root docs: `/home/christopherbailey/homelab-llm/SYSTEM_OVERVIEW.md`.
