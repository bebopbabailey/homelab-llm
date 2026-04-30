# Architecture: Open WebUI

Open WebUI is the UI layer. Requests flow from the browser to Open WebUI, then to
LiteLLM at `http://127.0.0.1:4000/v1`, which routes to model backends.

For native Knowledge, Open WebUI now uses the Studio retrieval stack in two
separate ways:
- storage/query path: direct Elasticsearch client through a Mini-local
  localhost bridge at `127.0.0.1:19200`
- embedding path: OpenAI-compatible `vector-db` embeddings at
  `http://192.168.1.72:55440/v1`

This keeps one shared Studio retrieval cluster while avoiding a raw LAN bind
for Elasticsearch.

Open WebUI also owns two localhost-only Open Terminal integrations on the Mini:
- native terminal UX on `127.0.0.1:8010`
- read-only MCP tool server on `127.0.0.1:8011/mcp`

These are tool-plane integrations only. They do not change the LiteLLM role for
LLM, STT, or TTS traffic.

Backend config is canonical. A post-restart reconciliation helper pushes the
canonical Knowledge/RAG settings into Open WebUI's retrieval runtime so the
admin UI reflects the same values.
