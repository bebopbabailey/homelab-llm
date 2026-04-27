# Runtime Planes

## Purpose
Define the current high-level architecture in terms of planes, not just
endpoints. This keeps the boring public contract separate from specialized
runtime systems and future orchestration.

## Plane 1: Commodity inference
- Public, boring, OpenAI-compatible, gateway-facing.
- Owned by the Mini-side control surface.
- Current examples:
  - LiteLLM on the Mini
  - Open WebUI and OpenCode as gateway clients
  - public `fast` and `deep` on the shared Studio `llmster` service
  - current OpenHands worker path through LiteLLM
- Success criteria:
  - predictable contracts
  - broad client compatibility
  - ordinary chat and ordinary tool use

## Plane 2: Specialized runtime
- Private, narrow, runtime-semantics-first.
- Owned by the Studio.
- Current architectural representative: `omlx-runtime`.
- This plane exists for workloads where runtime behavior matters more than a
  generic chat API, including:
  - repeated-prefix workloads
  - concurrent coding-agent workloads
  - cache-sensitive long-running generation
- This plane is not the commodity gateway contract.
- It is not assumed to be a public LiteLLM alias, Open WebUI backend, or
  universal OpenAI drop-in.

## Plane 3: Orchestration
- Future conductor layer for routing, branching, retries, evaluation, and state.
- Owned by Mini-side orchestration services by default.
- LangGraph belongs here conceptually because it is designed for long-running,
  stateful agent workflows rather than generic chat routing.
- LangChain may sit above or beside this plane as an application framework, but
  it is not the canonical runtime contract for provider-specific behavior.

## Execution boundary
- OpenHands is not the orchestration plane and not the specialized runtime
  plane.
- It remains a sandboxed operator and execution surface.
- Sandbox execution boundaries stay separate from both routing and runtime-plane
  decisions.

## Current policy
- Commodity-plane services may be public, alias-driven, and broadly compatible.
- Specialized runtime-plane services must keep a narrow contract and explicit
  ingress rules.
- Orchestration may call either plane later, but phase 1 does not implement
  that handoff.

## References
- oMLX README and release notes describe the runtime in terms of continuous
  batching, prefix sharing/CoW, and tiered KV cache:
  https://github.com/jundot/omlx/blob/main/README.md
  https://github.com/jundot/omlx/releases
- LangGraph overview:
  https://docs.langchain.com/oss/python/langgraph
- LangChain model/provider compatibility notes:
  https://docs.langchain.com/oss/python/langchain/models
  https://docs.langchain.com/oss/python/concepts/providers-and-models
- OpenHands sandbox/runtime docs:
  https://docs.openhands.dev/openhands/usage/sandboxes/overview
  https://docs.openhands.dev/openhands/usage/architecture/runtime
