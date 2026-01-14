# System Architecture (High Level)

This doc captures the platform-wide architecture and layer roles. Service-local
architecture belongs inside each service directory.

## Goal
Provide a single OpenAI-compatible gateway while allowing multiple specialist
backends (local and remote) to evolve independently.

## Layer 1 — Gateway (Front Door)
- **Service**: LiteLLM proxy
- **Role**: Single OpenAI-compatible API for all clients
- **Why**: Central routing point that hides backend complexity
- **Where**: Runs on the Mini for now

## Layer 2 — Orchestration (Planned)
- **Service**: TinyAgents (planned)
- **Role**: Choose specialist models, coordinate tool calls
- **Pattern**: Router–Coordinator

## Layer 3 — Specialist Backends
- **Local specialist**: OpenVINO GenAI server on the Mini (benny-*)
- **Remote specialists**: MLX OpenAI servers on the Studio (jerry/bench/utility)
- **Optimization proxy**: OptiLLM behind LiteLLM (localhost-only)

## Layer 4 — Model Registry & Conversion
- **MLX registry** (Studio): `mlxctl` manages fixed ports 8100–8109
- **OpenVINO registry** (Mini): `~/models/converted_models/registry.json`
- **Conversion**: `ov-convert-model` → OpenVINO IR + registry entries

## Data Flow (Typical)
1) Client sends request to LiteLLM.
2) LiteLLM maps logical model name to a backend.
3) Backend executes and returns response.
4) Optional: OptiLLM refinement loops (if enabled).

## Why This Is Durable
- Clear separation of routing vs inference.
- Single endpoint for clients; backends can change without client updates.
- Local services remain lightweight and always-on.
