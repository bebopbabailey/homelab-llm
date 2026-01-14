# System Overview

## Mission
Provide a single OpenAI-compatible entry point (LiteLLM) for all clients while
routing requests to multiple specialist backends. This keeps clients stable
while allowing backend models to evolve independently.

## Architecture (current + planned)
1) Front Door (current)
   - LiteLLM proxy is the single gateway for all clients.
2) Orchestration (planned)
   - TinyAgents will act as a client of LiteLLM, not a backend caller.
   - Orchestration owns task-level routing/retries; LiteLLM owns transport health
     checks and request logging.
3) Tooling (planned)
   - MCP servers provide tool access (search, ops, repo actions).
   - TinyAgents connects to MCP servers; LiteLLM remains the LLM gateway.
   - `search.web` and `web.fetch` run as stdio MCP tools for search + cleaning.
4) Optimization proxy (current)
   - OptiLLM runs localhost-only behind LiteLLM to apply inference-time strategies.
   - LiteLLM sends prefixed model names (e.g., `moa-jerry-xl`) to avoid loops.
5) Specialist Backends (current)
   - OpenVINO LLM server on the Mac Mini (`benny-*`).
   - MLX OpenAI servers on the Mac Studio (`jerry-*`).
   - AFM OpenAI-compatible API on the Studio (planned).
   - OpenVINO strength evaluation (planned): STT/vision/async throughput vs LLM latency.
   - Non-LLM model evaluation (planned): routing/classification, summarization, cleaning.
6) Search (current)
   - SearXNG runs locally on the Mini (127.0.0.1:8888) and is exposed via LiteLLM `/v1/search`.
   - `web.fetch` is the next step after search for clean content extraction.

## Data Flow (current)
1) Client sends an OpenAI-compatible request to LiteLLM.
2) LiteLLM maps a logical model name to a backend.
3) LiteLLM forwards to the backend and returns the response.

## Guiding Principles
- LiteLLM is the single gateway; clients must not call backends directly.
- Ports are treated as immutable without a migration plan.
- No new inference backends or LAN-exposed services without explicit approval.
- Use `uv` for Python dependency management; avoid system Python changes.

## MCP Status (current)
- `web.fetch` and `search.web` are implemented as stdio MCP tools.
- MCP registry and systemd wiring are MVP work items.

## Repo Layout (high-level)
- `docs/` — platform-wide architecture, constraints, topology.
- `platform/ops/` — operational scripts and systemd backup units.
- `layer-*/` — per-service code and contracts by layer.

## Glossary (short)
- LiteLLM gateway: single OpenAI-compatible front door for all clients.
- MLX servers: remote OpenAI-compatible backends on the Studio (ports 8100-8109).
- OpenVINO server: local lightweight backend on the Mini (port 9000).
- OptiLLM proxy: localhost-only optimization proxy behind LiteLLM (port 4020).
- TinyAgents: planned orchestration client that calls LiteLLM only.
