# OpenCode

## Purpose
OpenCode is the primary coding client for this repo. It uses LiteLLM presets
(`p-*` handles) and can invoke tools with explicit permission prompts.
 
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
- Models: use LiteLLM handles (e.g., `p-plan`, `p-seek`, `p-make`, `p-plan-max`)

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
opencode run -m litellm/p-seek "ping"
```

## Recommended aliases
- Default (planning): `p-plan`
- Fast: `p-seek`
- Balanced: `p-make`
- Deep: `p-plan-max`
- Prompt optimization: `p-opt-balanced`

## How I Use OpenCode (docs-first workflow)
This matches the repo’s docs-first + validation-heavy style and keeps churn low.

1) **Plan first (default)**
   - Start with `p-plan` for architecture, constraints, and phased plans.
   - Keep changes minimal; ask before touching multiple services.

2) **Draft + build (balanced)**
   - Switch to `p-make` when you begin edits.
   - Focus on concrete diffs and clear, reversible steps.

3) **Quick checks (fast)**
   - Use `p-seek` for quick spot checks, command ideas, and short questions.

4) **Deep refactor (max)**
   - Use `p-plan-max` only when a task needs heavy reasoning or multi-stage plans.

5) **Prompt optimizer (on-demand)**
   - Switch to `p-opt-balanced` when you need a clean prompt for another tool.
   - Switch back to `p-plan` after the prompt is generated.

6) **Always gate tools**
   - Keep `bash`/`edit` on `ask` to preserve the “approval gate” workflow.
