# Architecture: Open WebUI

Open WebUI is the UI layer. Requests flow from the browser to Open WebUI, then to
LiteLLM at `http://127.0.0.1:4000/v1`, which routes to model backends.

Open WebUI also owns two localhost-only Open Terminal integrations on the Mini:
- native terminal UX on `127.0.0.1:8010`
- read-only MCP tool server on `127.0.0.1:8011/mcp`

These are tool-plane integrations only. They do not change the LiteLLM role for
LLM, STT, or TTS traffic.
