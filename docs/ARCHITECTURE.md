# System Architecture (High Level)

This doc captures the platform-wide architecture and layer roles. Service-local
architecture belongs inside each service directory.

## Goal
Provide a single OpenAI-compatible gateway while allowing multiple specialist
backends (local and remote) to evolve independently.

## Layer 1 — Interface
- **Services**: Open WebUI, client entry points
- **Role**: Human-facing access and interaction

## Layer 2 — Gateway
- **Service**: LiteLLM proxy
- **Role**: Single OpenAI-compatible API for all clients
- **Why**: Central routing point that hides backend complexity
- **Where**: Runs on the Mini for now
 - **Monitoring**: system-monitor (planned) lives here
## Layer 3 — Inference
- **Local specialist**: OpenVINO GenAI server on the Mini (ov-*)
- **Remote specialists**: MLX OpenAI servers on the Studio (mlx-*; ports 8100-8119 team, 8120-8139 experimental).
- **MLX registry**: canonical `model_id` links to inference artifacts via `source_path`/`cache_path`.
- **Optimization proxy**: OptiLLM behind LiteLLM (localhost-only)
- **OptiLLM local**: Studio MPS/FP16 inference tier (ports 4040–4042)

## Layer 4 — Tools
- **Services**: MCP tools, web-fetch, search services (SearXNG)
- **Role**: Execute actions and retrieval

## Layer 5 — Data
- **Registry & conversion**: model registries and conversion metadata
- **System docs DB**: SQLite-first, Postgres-ready

## Orchestration (Planned, cross-layer)
- **Service**: TinyAgents (planned)
- **Role**: Choose specialist models, coordinate tool calls
- **Pattern**: Router–Coordinator

## Data Flow (Typical)
1) Client sends request to LiteLLM.
2) LiteLLM maps logical model name to a backend.
3) Backend executes and returns response.
4) Optional: OptiLLM refinement loops (if enabled).

## Why This Is Durable
- Clear separation of routing vs inference.
- Single endpoint for clients; backends can change without client updates.
- Local services remain lightweight and always-on.
