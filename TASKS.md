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
1) **[x] Registry and naming decisions**
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

2) **[x] Registry bootstrap (Studio)**
   - Enumerate existing HF cache folders under `~/models/hf/hub`.
   - Generate initial `registry.json` entries with `repo_id`, `model_id`, `cache_path`,
     and empty `port` unless a current assignment is known.
   - Use atomic write semantics (temp file + rename) and a file lock to avoid corruption.

3) **[x] MLX controller (Studio)**
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

4) **[x] MLX command entrypoint (Mini + Studio)**
   - Provide a single command (`mlxctl`) that accepts arguments on either host.
   - On Studio: `mlxctl` runs the controller locally.
   - On Mini: `mlxctl` forwards arguments over SSH to the Studio controller.

5) **[x] LiteLLM pre-registration**
   - Add the fixed aliases above to `layer-gateway/litellm-orch/config/router.yaml`
     and `config/env.example` with stable ports.
   - Ensure LiteLLM never needs a reload for model swaps as long as ports remain
     stable and managed by the MLX controller.
   - Configure LiteLLM `/v1/search` to proxy to SearXNG (LiteLLM is the only
     search endpoint clients hit; SearXNG stays behind it).

6) **[x] Web search via LiteLLM (Mini)**
   - Configure LiteLLM `/v1/search` to proxy to SearXNG.
   - Verify Open WebUI can call LiteLLM search (Open WebUI only targets LiteLLM).
   - Document Open WebUI search wiring in `docs/foundation`.

7) **AFM backend (Studio)**
   - Start AFM OpenAI-compatible API on the Studio (target: `:9999`).
   - Confirm `/v1/models` output and auth requirements (if any).
   - Add AFM base URL + model IDs to LiteLLM env and router config.
   - Document AFM in `docs/PLATFORM_DOSSIER.md`, `docs/foundation/topology.md`,
     and `docs/INTEGRATIONS.md`.

8) **OpenVINO strengths evaluation (Mini)**
   - Benchmark `benny-clean-*` with `OV_DEVICE=GPU`, `AUTO`, `MULTI:GPU,CPU`.
   - Capture single-request latency and concurrent throughput (2–4 requests).
   - Decide whether this host’s strengths are STT/vision/async throughput vs LLM.
   - Document results in `docs/journal/` and update `docs/PLATFORM_DOSSIER.md`.

9) **OpenVINO LLM follow-up (Mini)**
   - Evaluate int8 for `benny-extract-*`, `benny-summarize-*`, `benny-tool-*`.
   - Record quality + latency vs fp16; decide default routing per alias.
   - Assess int4 utility for LLMs on this iGPU stack (CPU-only vs GPU stability).
   - Decide whether IPEX-LLM is warranted to unlock GPU int4 paths.

10) **Non-LLM model evaluation (Mini)**
   - Validate ONNX route/classify + summarize baselines.
   - Evaluate non-LLM cleaning/extraction (punctuation/casing + rule pass).
   - Identify token-classification/NER options for extract/tool tasks.
   - Capture speed/quality notes in the journal.

11) **STT/TTS/Vision evaluation plan**
   - Select candidate models and formats (OpenVINO/ONNX).
   - Define minimal test set + metrics (latency, RTF, accuracy).
   - Run pilots and record results in `docs/journal/`.

12) **[x] OptiLLM wiring (move earlier)**
   - Point OptiLLM at one or more fixed aliases (e.g., `jerry-xl`) and ensure
     prefix-based loop avoidance (`moa-jerry-xl` into OptiLLM; `jerry-xl` upstream).
   - Add health checks and document the OptiLLM integration in `docs/foundation`
     and `docs/INTEGRATIONS.md`.

13) **Orchestration hub setup (Mini)**
   - Document the Mini as the orchestration host in core docs.
   - Reserve/track MCP server endpoints (stdio vs HTTP/SSE).
   - Define a stable tool naming convention (e.g., `search.web`, `repo.scan`).
   - Stand up a minimal MCP tool registry (server name, transport, purpose).
   - Start with local stdio MCP servers to avoid port sprawl.
   - Add an HTTP/SSE MCP server only when remote access is required.

14) **MCP MVP (Mini)**
  - Run a single MCP server on the Mini (stdio or HTTP/SSE).
  - Start with `search.web` only (LiteLLM `/v1/search` → SearXNG).
  - Add `web.fetch` (clean HTML → text) as a stdio MCP tool after search is stable.
  - Add `transcript.clean` after search + fetch are stable.
  - Add Home Assistant control via HA MCP Server after `transcript.clean`.
  - Add `mlx.load` / `mlx.unload` after HA control is stable.
  - Add these tools to the MCP registry and update `docs/foundation/mcp-registry.md`.
  - Copy `platform/ops/templates/mcp-registry.json` to `/etc/homelab-llm/mcp-registry.json`.
  - Add MCP server health checks in `platform/ops/scripts/healthcheck.sh`.
  - Near-term: add `transcript.clean` as a tool that injects the fixed prompt and
    calls `benny-clean-m` via LiteLLM to return only cleaned text.

15) **Agent routing (TinyAgents)**
   - Adapt TinyAgents to call LiteLLM (`http://127.0.0.1:4000/v1`).
   - Add a TinyAgents env file (model selection + tool server endpoints).
   - Copy `platform/ops/templates/tiny-agents.env` to `/etc/homelab-llm/tiny-agents.env`.
   - Add a minimal runner script that chooses agent type + tool set.
   - Add `ovctl` to manage OpenVINO warm-up profiles (`platform/ops/scripts/ovctl`).
   - Start with a single tool list (`search.web`) and expand after stability.

16) **Home-control readiness**
   - Add a permissions layer (safe vs confirmation-required tools).
   - Log tool calls with inputs, outputs, and request IDs.
   - Add a dry-run mode for home-control tools.

17) **Voice readiness (STT/TTS)**
   - Route STT text through TinyAgents (no direct tool access).
   - Route responses through TTS (same agent runtime, no bypass).

18) **Tool standardization**
   - Document each MCP tool contract (inputs/outputs, failure modes).
   - Version tool schemas to prevent breaking changes.
   - Add smoke tests for tool availability.
   - Plan a `python.run` MCP tool (sandboxed code execution) for future workflows.
   - Maintain Benny prompts in `docs/prompts/benny` and sync via `platform/ops/scripts/sync-benny-prompts`.

19) **Vector DB planning (Studio)**
   - Standardize on Qdrant (service on Studio), persist indexes on SSD.
   - Set explicit CPU/RAM limits (service flags or launchd) to avoid inference contention.
   - Add a simple tuning knob for max RAM/index cache size.
   - Add a controller command to adjust limits at runtime (or via config + restart).
   - Document expected resource usage and how to scale.

20) **Reliability and ops**
   - Add health checks for LiteLLM + MCP servers + TinyAgents runtime.
   - Add a reconcile step on boot to verify MCP availability.
   - Studio launchd should run `mlxctl reconcile` after default model startup.
   - Consolidate env files in a single location (e.g., `/etc/homelab-llm/`).

21) **Observability**
   - Log agent runs with request id, model, tool calls, latency, and errors.
   - Prefer JSON logs for future ingestion.

22) **[x] OpenVINO Benny aliases (Mini)**
  - Add `benny-*` models to LiteLLM router config.
  - Add `BENNY_*` env vars to `layer-gateway/litellm-orch/config/env.example`.
  - Add `BENNY_*` env vars to `layer-gateway/litellm-orch/config/env.local`.
  - Document Benny onboarding and mapping in `docs/foundation/benny-model-onboarding.md`.

## Constraints
- One port, one model (no shared ports).
- No Docker installs; use `uv` and repo conventions.
- LiteLLM remains the single gateway; OptiLLM is localhost-only.

## Nice-to-Haves
- [x] Add `mlxctl verify` to enforce required MLX flags and fail fast on drift.
- [x] Emit startup flag audit lines in `/opt/mlx-launch/logs/server.log` for traceability.
- Add a strict mode that refuses to start MLX when required flags are missing.
- Add Schematron (Inference.net) to the web-search pipeline for schema-first
  HTML → JSON extraction (docs: https://docs.inference.net/use-cases/json-extraction,
  model page: https://inference.net/models/schematron-3b).
- Add a reproducible conversion env file (pinned deps) and automate the
  Phi compatibility patch in the conversion flow (already scripted).
