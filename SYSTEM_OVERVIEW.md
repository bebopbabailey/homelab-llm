# System Overview

This monorepo powers the homelab AI stack. Services are organized by **layer** so
agents can operate with tight scopes. The gateway (LiteLLM) is the single entry
point for all model requests; backends are never called directly by clients.

## Layer map (summary)
- **Interface**: human-facing clients (Open WebUI)
- **Gateway**: routing/auth/observability (LiteLLM, OptiLLM, system monitor)
- **Inference**: model backends (OpenVINO, MLX/Studio, future AFM)
- **Tools**: MCP tools, search (SearXNG), actions
- **Data**: future vector/memory storage

## Principle
- **Everything goes through LiteLLM** unless explicitly documented otherwise.
- **New network exposure is opt-in**, never the default.
- **Services are independently serviceable** (submodules where active).

See `DOCS_CONTRACT.md` for the required docs at each level.
