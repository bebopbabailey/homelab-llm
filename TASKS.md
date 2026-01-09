# Tasks: MLX Registry + Port Manager + LiteLLM Pre-Registration

## Goal
Provide a durable MLX model registry on the Studio and a single controller
to load/unload models on ports 8100-8109, while keeping LiteLLM stable by
pre-registering fixed logical names per port. OptiLLM will be wired to these
stable aliases after the MLX and LiteLLM foundations are in place.

## Goal (Orchestration Hub)
Make the Mini the orchestration host for agent workflows:
- LLM calls go through LiteLLM only.
- Tool calls go through MCP servers.
- TinyAgents is the default lightweight client/orchestrator.
The end state is a personal assistant that grows by adding tools/services
without changing clients.

## Ordered Plan
1) **Registry and naming decisions**
   - Confirm MLX registry location on Studio: `/Users/thestudio/models/hf/hub/registry.json`.
   - Define MLX registry schema (versioned, compatible with OpenVINO registry shape):
     - `version: 1`
     - `models: { "<slug>": { repo_id, model_id, cache_path, format, port } }`
     - `port` represents current active port; one port per model; no duplicates allowed.
   - Confirm fixed LiteLLM model aliases for ports 8100-8109:
     - 8100 = `jerry-xl`
     - 8101 = `jerry-l`
     - 8102 = `jerry-m`
     - 8103 = `jerry-s`
     - 8104 = `bench-xl`
     - 8105 = `bench-l`
     - 8106 = `bench-m`
     - 8107 = `bench-s`
     - 8108 = `utility-a`
     - 8109 = `utility-b`
   - Create the MCP registry template and choose runtime location (`/etc/homelab-llm/mcp-registry.json`).

2) **Registry bootstrap (Studio)**
   - Enumerate existing HF cache folders under `~/models/hf/hub`.
   - Generate initial `registry.json` entries with `repo_id`, `model_id`, `cache_path`,
     and empty `port` unless a current assignment is known.
   - Use atomic write semantics (temp file + rename) and a file lock to avoid corruption.

3) **MLX controller (Studio)**
   - Build a Studio-side controller script (invoked via SSH from the Mini) with:
     - `list`: show registered models and their current ports.
     - `status`: show live ports vs registry assignments; highlight drift.
     - `load <model> <port>`:
       - Validate port is in 8100-8109 and not already assigned.
       - If port is already listening, refuse unless a `--force` flag is provided.
       - If model missing from registry, download from Hugging Face and register it
         (requires HF auth token if the model is gated).
       - Define how `<model>` maps to a registry entry (slug vs repo_id).
       - Start MLX server on the port and update registry once listening.
     - `unload <port>`:
       - Stop MLX server on port.
       - Clear registry `port` for the model previously assigned.
     - `reconcile`:
       - Verify registry matches actual listening ports and fix or report drift.

4) **MLX command entrypoint (Mini + Studio)**
   - Provide a single command (`mlxctl`) that accepts arguments on either host.
   - On Studio: `mlxctl` runs the controller locally.
   - On Mini: `mlxctl` forwards arguments over SSH to the Studio controller.

5) **LiteLLM pre-registration**
   - Add the fixed aliases above to `services/litellm-orch/config/router.yaml`
     and `config/env.example` with stable ports.
   - Ensure LiteLLM never needs a reload for model swaps as long as ports remain
     stable and managed by the MLX controller.
   - Configure LiteLLM `/v1/search` to proxy to SearXNG (LiteLLM is the only
     search endpoint clients hit; SearXNG stays behind it).

6) **Orchestration hub setup (Mini)**
   - Document the Mini as the orchestration host in core docs.
   - Reserve/track MCP server endpoints (stdio vs HTTP/SSE).
   - Define a stable tool naming convention (e.g., `search.web`, `repo.scan`).
   - Stand up a minimal MCP tool registry (server name, transport, purpose).
   - Start with local stdio MCP servers to avoid port sprawl.
   - Add an HTTP/SSE MCP server only when remote access is required.

7) **TinyAgents wiring**
   - Adapt TinyAgents to call LiteLLM (`http://127.0.0.1:4000/v1`).
   - Add a TinyAgents env file (model selection + tool server endpoints).
   - Add a minimal runner script that chooses agent type + tool set.

8) **Tool standardization**
   - Document each MCP tool contract (inputs/outputs, failure modes).
   - Version tool schemas to prevent breaking changes.
   - Add smoke tests for tool availability.

9) **Reliability and ops**
   - Add health checks for LiteLLM + MCP servers + TinyAgents runtime.
   - Add a reconcile step on boot to verify MCP availability.
   - Studio launchd should run `mlxctl reconcile` after default model startup.
   - Consolidate env files in a single location (e.g., `/etc/homelab-llm/`).

10) **Observability**
    - Log agent runs with request id, model, tool calls, latency, and errors.
    - Prefer JSON logs for future ingestion.

11) **OptiLLM wiring**
    - Point OptiLLM at one or more fixed aliases (e.g., `jerry-xl`) and ensure
      prefix-based loop avoidance (`moa-jerry-xl` into OptiLLM; `jerry-xl` upstream).
    - Add health checks and document the OptiLLM integration in `docs/foundation`
      and `docs/INTEGRATIONS.md`.

## Constraints
- One port, one model (no shared ports).
- No Docker installs; use `uv` and repo conventions.
- LiteLLM remains the single gateway; OptiLLM is localhost-only.

## Nice-to-Haves
- Add `mlxctl verify` to enforce required MLX flags and fail fast on drift.
- Emit startup flag audit lines in `/opt/mlx-launch/logs/server.log` for traceability.
- Add a strict mode that refuses to start MLX when required flags are missing.
