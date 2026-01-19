# Design Status (Working Notes)

Date: 2026-01-14

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
- No plan to move `/docs` out of repo root; it remains the system-level doc hub.

## Layer definitions (working)
- **Interface**: human-facing UI/clients (Open WebUI, Shortcuts endpoints)
- **Gateway**: request routing, auth, observability (LiteLLM + system monitoring)
- **Inference**: model backends and cognition (OpenVINO, MLX, AFM)
- **Tools**: action/execution (MCP tools, web fetch, HA control, SearXNG search)
- **Data**: user memory, summaries, logs as data products (not ops telemetry)

## Current layout (as of today)
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

  layer-tools/
    mcp-tools/
      web-fetch/
    searxng/                  # search service (via LiteLLM /v1/search)

  layer-data/
    vector-db/                # RAG storage (if used here)

  docs/                       # system-level docs (stay at root)

  platform/
    ops/                      # moved from /ops
```

## Runtime reality (Mini)
- systemd units installed/enabled: LiteLLM, Open WebUI, OpenVINO LLM, SearXNG, OptiLLM.
- All five are now running with venvs recreated under the layer paths.
- SearXNG still runs on localhost:8888 (not exposed on LAN).

## Runtime reality (Studio)
- LaunchDaemon: `com.bebop.mlx-launch` is enabled and running at boot.
- `com.deploy.mlx.server.plist.disabled` exists and remains disabled by design.

## Monitoring placement (decision)
- **System monitoring is part of the Gateway layer** because:
  - LiteLLM is the single entry point for requests.
  - Health, errors, latency, and model routing are visible there.
  - Monitoring is ops telemetry, not user memory.
  - Monitoring views are derived from the system documentation DB.


## Documentation + Registry Integration (current stance)
- System documentation DB is the single source of truth (SQLite-first, migrate to Postgres).
- Registries live as DB tables/views, not scattered flat files long-term.
- Monitoring is derived from DB views (no separate monitoring truth source).
- Registries are minimal + actionable, with pointers to richer service docs.
- Models are first-class entities with richer metadata; may link to a model-focused DB later.
- System monitor is a gateway-layer service (not embedded inside LiteLLM).
- Gateway v0: the only live registry is `handles.jsonl` (routing handles). Endpoint and policy registries are deferred.
  - Planned models table should include size-on-disk / memory footprint for ordering and capacity planning.
  - MLX registry uses `model_id` → `source_path` / `cache_path` for durable artifact resolution.

## Open questions to resolve
- Which registries should be centralized vs strictly service-local?
- Should `layer-data/registries/` be an index only (links), or store live files?


## Layer Documentation Philosophy
- Layer docs should not be uniform beyond a minimal floor.
- **Required per layer:** `README.md` (mission/scope) and `CONSTRAINTS.md` (non‑negotiables).
- Everything else is **layer‑specific**, based on responsibility and failure modes:
  - Gateway: contracts, routing rules, auth, escalation boundaries.
  - Inference: runtime configs, device constraints, model loading, perf notes.
  - Tools: safety boundaries, external call policies, rate limits.
  - Interface: UI config, upstream expectations.
  - Data: lifecycle, retention, schema evolution.


## Sandbox Permissions (Draft)
- Defined in `SANDBOX_PERMISSIONS.md` and mirrored in each layer CONSTRAINTS.md.
- Root agent: read-only across repo; can run diagnostics only.
- Layer agents: read/write within their layer; can restart services in that layer only.
- Service agents: full control within their service; must respect global constraints.
- CONSTRAINTS.md will be folded into AGENTS.md later; keep CONSTRAINTS in layer docs for now.
