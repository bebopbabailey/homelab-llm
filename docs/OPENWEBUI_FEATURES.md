# Open WebUI: Feature Map + Admin Settings Guide

This document is a concise, power-user map of Open WebUI features with emphasis
on **Admin Panel → Settings**. It combines what the official docs describe with
practical notes for this homelab.

Sources are cited inline for durability. Always confirm in the UI because
Open WebUI evolves quickly.

---

## 1) Feature Map (high‑level)

**Core platform capabilities (documented)**
- Model builder + presets + base model binding. citeturn2search0
- RAG features: document/URL ingestion and web search for RAG. citeturn1search4
- Tools/functions + integration types (workspace tools, OpenAPI servers, MCP via proxy). citeturn0search0
- Pipelines for heavier workflows. citeturn0search5
- Admin controls: roles, permissions, RBAC. citeturn1search1turn1search0turn1search3

**Why this matters for MCP**
Open WebUI already has tooling + pipeline concepts. MCP should be used for
tool execution that you **want to centralize, secure, and reuse** across
clients, not only in Open WebUI.

---

## 2) Admin Panel → Settings (documented areas)

> Note: The official docs list features, but not every Admin Settings field is
> fully enumerated. Use this map + the UI itself to confirm.

### A) Web Search
Open WebUI supports web search via providers such as **SearXNG**, with settings
available under Admin Panel → Settings → Web Search. citeturn0search1

Key documented behaviors:
- **SearXNG Query URL must include** `/search?q=<query>` (mandatory). citeturn0search1
- **Per‑chat toggle**: Web search must be toggled on in each chat session and
  resets when you switch chats or reload. citeturn0search1
- **JSON format required**: SearXNG must expose JSON results or Open WebUI will
  block queries. citeturn0search1

Recommended defaults for this homelab:
- Search Result Count: 5–7
- Concurrent Requests: 2–4
- Domain Filter: empty globally; use a personal filter when you want tight sources

### B) Models / Model Presets
Open WebUI’s Model Builder lets you create presets with:
- Display name + unique ID
- Base model selection
- Optional fallback behavior when a model is unavailable (controlled by env). citeturn2search0turn2search2

Model capability toggles (per model preset):
- Web Search, File Upload, Code Interpreter, Image Generation, etc. citeturn2search0

For this homelab:
- Point base models to LiteLLM logical names (`mlx-*`, `ov-*`).
- Keep fallbacks conservative; prefer explicit routing in LiteLLM.

### C) Tools / Functions
Open WebUI supports:
- Workspace Tools (Python scripts run inside Open WebUI). citeturn0search0
- OpenAPI servers (HTTP integrations) via Settings → Connections. citeturn0search0
- MCP via proxy (MCPO adapter) via Settings → Connections. citeturn0search0

### D) Pipelines
Open WebUI supports pipelines that can be connected via Admin Panel → Settings
→ Connections, and configured under the Pipelines tab. citeturn0search5

Why this matters:
Pipelines are Open WebUI‑specific. MCP tools are **platform‑wide**. Use
pipelines for UI‑local enhancements; use MCP for shared services.

---

### E) External Tools (MCP)
Open WebUI supports MCP (Streamable HTTP) starting in v0.6.31.
Add MCP servers in Admin Settings → External Tools. citeturn0search2

Important constraints from the docs:
- Open WebUI supports MCP over **Streamable HTTP only** (not stdio or SSE). citeturn0search2
- OpenAPI is the preferred integration path for many deployments. citeturn0search2

This is why we keep stdio MCP tools (like `web.fetch`) behind TinyAgents and
avoid exposing them directly to Open WebUI.

---

## 3) What to keep inside Open WebUI vs MCP

**Keep in Open WebUI**
- UI preferences and model presets
- Web Search provider configuration (SearXNG URL, concurrency, results)
- Optional pipelines for UI‑local enhancement

**Move to MCP**
- Any tool you want to use from multiple clients (Open WebUI, voice, scripts)
- Tooling that should be versioned, audited, or sandboxed
- HTML fetch/clean steps (e.g., `web.fetch`) and other pre‑processing utilities

---

## 4) Practical Admin Settings Checklist (for this homelab)

**Web Search**
- Enable Web Search
- Engine: SearXNG
- Query URL: `http://127.0.0.1:8888/search?q=<query>` citeturn0search1
- Result count: 5–7
- Concurrency: 2–4
- Language: `en` (or `all` if needed)

**Models**
- Set default models to LiteLLM aliases (no direct backend URLs)
- Avoid large numbers of presets; use a few meaningful workflows

**Pipelines**
- Only enable if you need UI‑specific workflows
- MCP is the preferred tool layer for cross‑client reuse

---

## 5) Future MCP integration plan (short)

1) Keep Open WebUI web search for UI convenience.
2) Use MCP for structured fetch/clean (`web.fetch`) and specialized tools.
3) Let TinyAgents orchestrate tool calls outside the UI for voice + automation.

---

## References
Open WebUI feature overview:  
`https://docs.openwebui.com/features` citeturn1search5

Open WebUI models workspace:  
`https://docs.openwebui.com/features/workspace/models/` citeturn2search0

Open WebUI SearXNG setup:  
`https://docs.openwebui.com/tutorials/web-search/searxng/` citeturn0search1

Open WebUI pipelines:  
`https://docs.openwebui.com/pipelines/` citeturn0search5

Open WebUI tools (function calling modes):  
`https://docs.openwebui.com/features/plugin/tools/` citeturn0search0

Open WebUI MCP support:  
`https://docs.openwebui.com/features/mcp/` citeturn0search2

Open WebUI RBAC:  
`https://docs.openwebui.com/features/rbac/` citeturn1search1

Open WebUI permissions:  
`https://docs.openwebui.com/features/rbac/permissions/` citeturn1search0turn1search1
