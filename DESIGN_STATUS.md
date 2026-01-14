# Design Status (Working Notes)

Date: 2026-01-13

This document captures the current design direction so we stay organized while
restructuring the repo. It is intentionally short and will be refined later.

## Current direction (agreed)
- Services should be **independently serviceable** with a consistent doc pack
  (README, SERVICE_SPEC, ARCHITECTURE, AGENTS, TASKS, RUNBOOK, plus `docs/`).
- Root-level docs focus on **system architecture and integration**, not service internals.
- Use a **layered directory tree** with technical names (Option C: Interface, Gateway,
  Inference, Tools, Data). Services have been moved into layers via IntelliJ.
- **System monitoring** should live at the **Gateway layer** (LiteLLM is the source
  of monitoring signals and health data).
- **System documentation DB** is the single source of truth (SQLite-first with a
  Postgres migration path). Model registries live here as first-class entities.
- **Monitoring** is derived from views over this DB, not a separate truth source.
- Schema: `docs/foundation/system-docs-db-schema.md`.

## Layer definitions (working)
- **Interface**: human-facing UI/clients (Open WebUI, Shortcuts endpoints)
- **Gateway**: request routing, auth, observability (LiteLLM + system monitoring)
- **Inference**: model backends and cognition (OpenVINO, MLX, AFM)
- **Tools**: action/execution (MCP tools, web fetch, HA control, SearXNG search)
- **Data**: user memory, summaries, logs as data products (not ops telemetry)

## Proposed root layout (target)
```text
homelab-llm/
  layer-interface/
    open-webui/

  layer-gateway/
    litellm-orch/
    system-monitor/           # placeholder service
    optillm-proxy/            # optimization proxy behind LiteLLM
    tiny-agents/              # orchestration client

  layer-inference/
    ov-llm-server/
    orin-llm-server/          # future inference host
    mlx-backends/             # docs/config only if needed
    afm/                      # planned

  layer-tools/
    mcp-tools/
      web-fetch/
      search-web/             # if split later
      home-assistant/         # planned
    searxng/                  # search service (via LiteLLM /v1/search)

  layer-data/
    vector-db/                # RAG storage (if used here)
    memory/                   # user/context memory (RAG-able)
    summaries/                # derived summaries
    registries/               # index or exports from the system documentation DB

  platform/
    ARCHITECTURE.md
    PLATFORM_DOSSIER.md
    INTEGRATIONS.md
    constraints-and-decisions.md
    topology.md
    journal/
    ops/
    TASKS.md
```

## Monitoring placement (decision)
- **System monitoring is part of the Gateway layer** because:
  - LiteLLM is the single entry point for requests.
  - Health, errors, latency, and model routing are visible there.
  - Monitoring is ops telemetry, not user memory.
  - Monitoring views are derived from the system documentation DB.

## Open questions to resolve
- Which registries should be centralized vs strictly service-local?
- Should `layer-data/registries/` be an index only (links), or store live files?
