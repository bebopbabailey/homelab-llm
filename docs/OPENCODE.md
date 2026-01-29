# OpenCode

## Purpose
OpenCode is the primary coding client for this repo. It uses LiteLLM aliases
(`main`/`deep`/`fast`/`swap` handles) and can invoke tools with explicit permission prompts.
 
## Install (MacBook)
Opencode installs into `~/.opencode/bin/opencode`. Ensure it is on PATH:
```bash
mkdir -p ~/.local/bin
ln -sf "$HOME/.opencode/bin/opencode" "$HOME/.local/bin/opencode"
```

## Config
Config file:FlFloF
- `~/.config/opencode/opencode.json`

Provider setup (LiteLLM OpenAI-compatible):
- Base URL: `http://100.69.99.60:4000/v1`
- Models: use LiteLLM handles (e.g., `main`, `deep`, `fast`, `swap`)

Permissions:
- Use `permission` rules to require approval (e.g., `bash: "ask"`, `edit: "ask"`).
- The legacy `tools` config still works, but `permission` is the supported control plane.
  (Legacy `tools` booleans are deprecated upstream.)

## Web Search (SearXNG via LiteLLM)
OpenCode uses MCP for tools. The recommended MCP server is the local `web-fetch`
stdlib tool, which exposes:
- `search.web` (calls LiteLLM `/v1/search/searxng-search`)
- `web.fetch` (clean URL extraction)

MCP server config (in `opencode.json`):
```json
"mcp": {
  "web-fetch": {
    "type": "local",
    "command": ["/Users/christopherbailey/.local/share/mcp/web-fetch/.venv/bin/web-fetch-mcp"],
    "enabled": true,
    "environment": {
      "LITELLM_SEARCH_API_BASE": "http://100.69.99.60:4000/v1/search/searxng-search",
      "LITELLM_SEARCH_API_KEY": "dummy"
    }
  }
}
```

## Quick commands
List models:
```bash
opencode models litellm
```

List MCP servers:
```bash
opencode mcp list
```

Start (TUI):
```bash
opencode
```

One-shot run:
```bash
opencode run -m litellm/main "ping"
```

## Recommended aliases
- Default: `main`
- Fast: `fast`
- Deep: `deep`

## How I Use OpenCode (docs-first workflow)
This matches the repo’s docs-first + validation-heavy style and keeps churn low.

1) **Plan first (default)**
   - Start with `main` for architecture, constraints, and phased plans.
   - Keep changes minimal; ask before touching multiple services.

2) **Draft + build (fast)**
   - Switch to `fast` when you begin edits.
   - Focus on concrete diffs and clear, reversible steps.

3) **Quick checks (fast)**
   - Use `fast` for quick spot checks, command ideas, and short questions.

4) **Deep refactor**
   - Use `deep` only when a task needs heavy reasoning or multi-stage plans.

5) **Always gate tools**
  - Keep `bash`/`edit` on `ask` to preserve the “approval gate” workflow.
