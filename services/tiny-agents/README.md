# TinyAgents (planned)

## Overview
TinyAgents is a minimalist agent implementation that uses LLMs plus MCP tools.
Upstream project: `https://github.com/albertvillanova/tinyagents`.

In this homelab, TinyAgents is planned as a **client/orchestrator** that calls
LiteLLM only. It must not call backends directly.

## Status and Constraints
- MCP is allowed, but should be planned and documented before enabling.
- No new LAN-exposed services without approval.
- Use `uv` for Python dependency management.

## Install (uv-only)
TinyAgents is a small repo with a `pyproject.toml`. Install from a pinned commit:

```bash
cd /home/christopherbailey/homelab-llm/services/tiny-agents
uv venv .venv
uv pip install "tinyagents @ git+https://github.com/albertvillanova/tinyagents.git@<PINNED_COMMIT>"
```

## Configuration
- TinyAgents uses Hugging Face InferenceClient upstream by default.
- If using HF, set `HUGGINGFACEHUB_API_TOKEN` (or the token your HF client reads).
- For homelab integration, adapt TinyAgents to call LiteLLM instead of Hugging Face.
  LiteLLM base URL: `http://127.0.0.1:4000/v1`.

## Usage (upstream examples)
Upstream scripts (from the repo):

```bash
python tinytoolcallingagent.py servers/weather/weather.py
python tinycodeagent.py servers/weather/weather.py
```

## MCP smoke (local tools)
Use the web-fetch MCP server to validate `search.web` and `web.fetch`:

```bash
cd /home/christopherbailey/homelab-llm/services/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 /home/christopherbailey/homelab-llm/services/tiny-agents/scripts/mcp_smoke.py --tool search.web
```

## References
- Upstream README: `https://github.com/albertvillanova/tinyagents`
- MCP overview: `https://modelcontextprotocol.io/`
