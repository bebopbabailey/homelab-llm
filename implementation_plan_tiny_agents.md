# Implementation Plan

[Overview]
Implement TinyAgents as a local tool-capable agent with both CLI and localhost-only HTTP service modes that routes all LLM traffic through LiteLLM.

This plan introduces a small, uv-managed Python package under `layer-gateway/tiny-agents/` that provides (1) a CLI runner for interactive/one-shot tasks, and (2) an HTTP service wrapper bound to `127.0.0.1:4030` for programmatic use.

The intent is to create a controlled autonomy “experiment harness”: the agent can call MCP tools via the registry at `/etc/homelab-llm/mcp-registry.json`, and can call models via LiteLLM only (`http://127.0.0.1:4000/v1`). This keeps backends (MLX, OpenVINO, OptiLLM proxy, etc.) behind the gateway contract.

We will keep scope small and safe:
- **No LAN exposure** (service binds to localhost only).
- **No privileged execution** (no shell execution tools, no file writes outside an explicit allowlist).
- **Tool creation** is implemented as scaffolding only (generate a new MCP tool skeleton in a specific repo directory), and does not auto-enable the tool at runtime.

[Types]
Add minimal request/response schemas for the TinyAgents HTTP service and internal configuration.

### Runtime configuration

`TinyAgentsSettings`
- `litellm_api_base: str` (required)
  - default: `http://127.0.0.1:4000/v1`
  - validation: must start with `http://127.0.0.1:` (local-only for MVP)
- `litellm_api_key_env: str` (required)
  - default: `LITELLM_API_KEY`
  - validation: non-empty env var name; value must be provided at runtime (not committed)
- `mcp_registry_path: str` (required)
  - default: `/etc/homelab-llm/mcp-registry.json`
  - validation: file must exist for tool use; if missing, tools are disabled with a clear error
- `allowed_tools: list[str]` (optional)
  - default: all tools in the registry
  - validation: if provided, every tool must exist in registry

`McpServerSpec` (parsed from registry JSON)
- `name: str`
- `purpose: str`
- `transport: Literal["stdio", "http"]`
- `command: str` (for stdio)
- `args: list[str]`
- `env: list[str]` (names of env vars to pass through)
- `tools: list[str]`

### HTTP API models (FastAPI)

`ChatMessage`
- `role: Literal["system", "user", "assistant", "tool"]`
- `content: str`

`RunRequest`
- `model: str` (required)
  - example: `main`, `deep`, `fast`, `boost`
- `messages: list[ChatMessage]` (required)
- `allowed_tools: list[str] | null` (optional override)
- `max_tool_calls: int` (default: 8)
- `timeout_s: int` (default: 120)
- `run_id: str | null` (optional; if omitted, server generates)

`ToolCallRecord`
- `tool_name: str`
- `input_json: object`
- `output_json: object | null`
- `error: str | null`

`RunResponse`
- `run_id: str`
- `model: str`
- `tool_calls: list[ToolCallRecord]`
- `final_message: ChatMessage`
- `stats: object` (token/cost fields optional; do not rely on them)

[Files]
Create a uv-managed Python package with both CLI and service entrypoints, plus minimal docs and smoke checks.

### New files
- `implementation_plan_tiny_agents.md`
  - This plan.

- `layer-gateway/tiny-agents/pyproject.toml`
  - uv project for TinyAgents runner.

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/__init__.py`
- `layer-gateway/tiny-agents/src/homelab_tiny_agents/settings.py`
  - Parse env + defaults; validate “local-only” constraints.

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/mcp_registry.py`
  - Load and validate `/etc/homelab-llm/mcp-registry.json`.

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/mcp_client.py`
  - Stdio MCP client wrapper (using `mcp` library).

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/litellm_client.py`
  - Minimal OpenAI-compatible client (httpx) targeting LiteLLM.

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/agent.py`
  - Core loop: model → tool call(s) → final answer.
  - Enforces `allowed_tools`, `max_tool_calls`, and timeouts.

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/cli.py`
  - CLI entrypoint.

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/service.py`
  - FastAPI app + routes: `/health`, `/run`.

- `layer-gateway/tiny-agents/src/homelab_tiny_agents/tool_scaffold.py`
  - `scaffold-tool` command that generates a new MCP stdio server skeleton.
  - Writes only under `layer-tools/mcp-tools/<tool-name>/`.

- `layer-gateway/tiny-agents/scripts/smoke_tiny_agents.sh`
  - Local smoke (CLI) and (optional) service request.

### Existing files to modify
- `layer-gateway/tiny-agents/README.md`
  - Replace “install upstream tinyagents” placeholder with local package install (`uv sync`) and usage examples.

- `layer-gateway/tiny-agents/SERVICE_SPEC.md`
  - Update to include service mode details:
    - bind `127.0.0.1`, port `4030`
    - endpoints and expected behavior.

- `layer-gateway/tiny-agents/RUNBOOK.md`
  - Add local service start/stop instructions (local-only; no LAN exposure).
  - Keep systemd optional (documented but not required for MVP).

- `platform/ops/templates/tiny-agents.env`
  - Add `TINY_AGENTS_PORT=4030` and optional `TINY_AGENTS_HOST=127.0.0.1`.

### Files not to change
- No edits to Orin/Jetson services.
- No changes to existing ports/binds for other services.

[Functions]
Add a small set of functions implementing the agent core, MCP invocation, and service endpoints.

### New functions (representative)
- `homelab_tiny_agents.settings.load_settings() -> TinyAgentsSettings`
- `homelab_tiny_agents.mcp_registry.load_registry(path: str) -> list[McpServerSpec]`
- `homelab_tiny_agents.mcp_client.call_tool(tool_name: str, input_json: dict) -> dict`
- `homelab_tiny_agents.litellm_client.chat_completions(model: str, messages: list[ChatMessage], **kwargs) -> dict`
- `homelab_tiny_agents.agent.run_agent(model: str, messages: list[ChatMessage], allowed_tools: list[str] | None, ...) -> RunResponse`
- `homelab_tiny_agents.service.health() -> dict`
- `homelab_tiny_agents.service.run(req: RunRequest) -> RunResponse`
- `homelab_tiny_agents.tool_scaffold.scaffold_tool(name: str, dest_root: str) -> None`

### Modified functions
- None (TinyAgents currently has no code; only docs/scripts).

[Classes]
Prefer lightweight dataclasses/Pydantic models; keep classes minimal.

### New classes
- `TinyAgentsSettings` (Pydantic BaseModel)
- `McpServerSpec` (Pydantic BaseModel)
- `RunRequest`, `RunResponse`, `ChatMessage`, `ToolCallRecord` (Pydantic BaseModel)

### Modified classes
- None.

[Dependencies]
Introduce a minimal uv-managed dependency set for the TinyAgents runner.

Planned dependencies (pin via `pyproject.toml`, then `uv.lock` will update):
- `fastapi`
- `uvicorn`
- `httpx`
- `pydantic`
- `mcp`

Notes:
- Keep dependencies minimal; avoid adding optional frameworks.
- No docker.
- No new LAN exposure; service must bind to `127.0.0.1`.

[Testing]
Validate with smoke tests (FAST) rather than heavy unit suites initially.

### Smoke checks
1) CLI:
   - run a prompt that calls `search.web` and returns tool output.
2) Service:
   - `GET /health` returns OK.
   - `POST /run` with a simple prompt triggers at most one tool call and returns JSON.

### Validation strategy
- Reuse existing MCP smoke (`scripts/mcp_smoke.py`) as a tool-layer prerequisite.
- Add TinyAgents smoke script that:
  - asserts MCP registry loads
  - asserts LiteLLM reachable
  - verifies tool allowlist enforcement

[Implementation Order]
Implement CLI-first (usable immediately), then wrap it in a local-only HTTP service, then add tool scaffolding.

1) Create `layer-gateway/tiny-agents/pyproject.toml` and package skeleton under `src/homelab_tiny_agents/`.
2) Implement config + MCP registry loader and verify existing `web-fetch` MCP server works.
3) Implement LiteLLM client and a minimal agent loop that can call 1 tool.
4) Add CLI entrypoint + docs examples.
5) Add FastAPI service (`127.0.0.1:4030`) reusing the same agent core.
6) Add `scaffold-tool` command (writes only under `layer-tools/mcp-tools/`).
7) Add smoke scripts and update runbooks/specs/templates.
