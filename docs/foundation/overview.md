# System Overview

## Mission
Provide a boring commodity inference surface for ordinary clients while keeping
specialized runtimes and future orchestration as separate architectural planes.
This keeps public contracts stable without forcing every useful runtime to
pretend it is just another generic gateway backend.

## Architecture (current + planned)
Reference: `docs/foundation/runtime-planes.md`

1) Commodity inference plane (current)
   - LiteLLM is the public gateway for ordinary clients.
   - Open WebUI, OpenCode, and current OpenHands worker traffic live here.
2) Specialized runtime plane (current, narrow)
   - Studio-local specialized runtimes may exist outside the commodity gateway
     contract when their value is runtime behavior rather than broad
     compatibility.
   - Current architectural representative: `omlx-runtime`.
3) Orchestration plane (planned)
   - TinyAgents is the current repo-owned orchestration foothold.
   - Future orchestration owns task-level routing, retries, state, and
     evaluation rather than flattening those concerns into the commodity
     gateway.
4) Tooling (planned)
   - MCP servers provide tool access (search, ops, repo actions).
   - TinyAgents connects to MCP servers; LiteLLM remains the LLM gateway.
   - `search.web` and `web.fetch` run as stdio MCP tools for search + cleaning.
5) Optimization proxy (current)
   - OptiLLM runs on the Studio (`192.168.1.72:4020`) and is consumed through LiteLLM `boost` handles over the LAN contract.
   - Clients include `optillm_approach` in the request body when they want to override default router behavior.
   - Single OptiLLM instance serves both `boost` and `boost-deep`.
6) Specialist backends (current)
   - OpenVINO LLM server on the Mac Mini (standalone backend; not currently wired as active LiteLLM handles).
   - MLX `vllm-metal` lanes on the Mac Studio (`8100/8101/8102`, registry-driven via `mlxctl` + `com.bebop.mlx-launch`).
   - AFM OpenAI-compatible API on the Studio (planned).
   - OpenVINO strength evaluation (planned): STT/vision/async throughput vs LLM latency.
   - Non-LLM model evaluation (planned): routing/classification, summarization, cleaning.
7) Search (current)
   - SearXNG runs locally on the Mini (127.0.0.1:8888) and is exposed via LiteLLM `/v1/search`.
   - `web.fetch` is the next step after search for clean content extraction.

## Data Flow (current)
1) Commodity-plane clients send OpenAI-compatible requests to LiteLLM.
2) LiteLLM maps logical names to commodity-plane backends.
3) LiteLLM forwards to the backend and returns the response.
4) Specialized runtimes are not assumed to traverse the same public alias path.

## Guiding Principles
- LiteLLM is the commodity-plane gateway; ordinary clients must not call
  commodity backends directly.
- Not every useful runtime belongs in the commodity plane.
- Tool calls are a separate plane from LLM calls; localhost-only Open WebUI
  tool connections are allowed when they use a documented MCP or terminal
  server, not a model backend.
- Ports are treated as immutable without a migration plan.
- No new inference backends or LAN-exposed services without explicit approval.
- Use `uv` for Python dependency management; avoid system Python changes.

## MCP Status (current)
- `web.fetch` and `search.web` are implemented as stdio MCP tools.
- The TinyAgents-facing MCP registry exists at `/etc/homelab-llm/mcp-registry.json`.
- Open Terminal MCP is live as a localhost-only systemd-backed service on Mini
  and remains separate from the TinyAgents registry.
- Open WebUI directly uses the local Open Terminal surfaces on Mini:
  native terminal on `127.0.0.1:8010` plus a read-only MCP tool server on
  `127.0.0.1:8011/mcp`.
- A shared LiteLLM MCP alias for the read-only subset is still follow-on work,
  not current runtime truth.

## Repo Layout (high-level)
- `docs/` — platform-wide architecture, constraints, topology.
- `platform/ops/` — operational scripts and systemd backup units.
- `layer-*/` — per-service code and contracts by layer.

## Glossary (short)
- LiteLLM gateway: single OpenAI-compatible front door for all clients.
- MLX servers: remote OpenAI-compatible backends on the Studio (team ports 8100-8119; experimental 8120-8139).
- MLX registry maps canonical `model_id` to `source_path`/`cache_path` for inference.
- OpenVINO server: local lightweight backend on the Mini (port 9000).
- OptiLLM proxy (Studio): optimization proxy on port 4020; used primarily via LiteLLM `boost`.
- OptiLLM local: not deployed on Orin. The host is available, but any Orin-local inference work still requires a separate approved plan.
- TinyAgents: planned orchestration client that calls LiteLLM only.
- `omlx-runtime`: specialized runtime-plane service identity for oMLX-style
  workloads; not part of the public commodity gateway contract.
