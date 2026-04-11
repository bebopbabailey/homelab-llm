# Local Specialist Mesh with Single-Endpoint Front Door

## Goal
Provide a single OpenAI-compatible endpoint while enabling multiple models to collaborate
as a “board of specialists.” This Mac Mini hosts a lightweight OpenVINO backend (external
service) and serves as one specialist node.

## Layer 1 — Front Door (Single Endpoint) (Current)
- **Service**: LiteLLM proxy
- **Role**: Unified OpenAI-compatible API for all clients (UI, agents, scripts)
- **Why**: Central routing point that hides backend complexity and supports multiple providers
- **Where**: Runs on this Mac Mini for simplicity (can move later)

## Layer 2 — Orchestration & Routing (Planned)
- **Service**: tinyagents (planned), optional OptiLLM loops
- **Role**: Decide which specialist models to call, aggregate responses, refine prompts
- **Pattern**: Router-Coordinator
    - Router model picks the best specialist(s) for the request
    - Coordinator merges or refines results into one response
- **Why**: Mix fast/cheap models with slow/accurate ones without changing clients
 - **Boundary**: tinyagents owns orchestration logic (model selection, retries at task level); the gateway owns transport health checks, routing availability, and request logging.

## Layer 3 — Specialist Backends (Current)
- **Local specialist (machine)**:
    - OpenVINO GenAI server on the Mac Mini (external service, not in this repo)
    - Exposed to the gateway as `ov-*`
    - Lightweight models for classification, tool calls, quick instruction following
    - Optimized for low-resource, always-on use
- **Remote specialist (big box)**:
    - Heavy-inference models for deep reasoning and generation
    - Accessed through LiteLLM as another backend (MLX `vllm-metal` lanes on the Studio)
    - AFM OpenAI-compatible API on the Studio (planned)

## Data Flow (Current)
1. Client sends an OpenAI-compatible request to LiteLLM.
2. LiteLLM routes based on the requested logical model name.
3. LiteLLM forwards to the chosen backend:
    - Local OpenVINO server (external service on this Mini, mapped as `ov-*`), or
    - Remote heavy-inference machine (MLX `vllm-metal` lanes on the Studio).
4. LiteLLM returns the upstream response to the client.

## Data Flow (Planned)
1. Client sends an OpenAI-compatible request to LiteLLM.
2. Router decides which backend model(s) to call.
3. LiteLLM forwards to the chosen backend(s).
4. Coordinator returns a single response to the client.
5. Optional: OptiLLM or teacher/student refinement loops run between steps 2–4.

## Naming Conventions
- `mlx-*` logical models target MLX servers on the Studio.
- Canonical format: `mlx-<family>-<params>-<quant>-<variant>` in that order.
- `ov-*` targets the local OpenVINO backend on the Mini.

## TinyAgents Integration (Planned)
- TinyAgents will be an orchestration client that sends OpenAI-compatible requests to LiteLLM.
- LiteLLM remains the single API entry point; TinyAgents should never call backends directly.
- Model selection and task-level retries live in TinyAgents; transport health checks and request logging stay in LiteLLM.

## Why This Is Durable
- Clear separation of routing vs inference.
- Single endpoint for clients; direct backends still available for one-offs.
- Easy to add/remove specialists without changing clients.
- Keeps the Mac Mini lightweight, reliable, and power-efficient.
