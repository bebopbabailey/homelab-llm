# Service Spec: omlx-runtime

## Purpose
Represent the specialized runtime plane in the repo as a narrow,
non-commodity runtime contract centered on oMLX.

## Status
- Experimental
- Repo-defined thin ingress client; still not a deployed shared service
- Not part of the active LiteLLM alias surface
- Not part of the active Open WebUI backend contract

## Host & ownership
- Intended host: Studio
- Intended runtime class: long-running specialized inference runtime
- Plane: specialized runtime

## Contract
- Allowed workload class:
  - repeated-prefix generation
  - concurrent coding-agent workloads
  - cache-sensitive long-running generation
- Intended callers:
  - direct operator probes
  - future thin dedicated adapters
  - future orchestration-plane services
- Explicit non-goals:
  - public commodity chat lane
  - generic LiteLLM alias
  - Open WebUI default backend
  - automatic fallback target
  - provider normalization
  - semantic request rewriting
  - generalized OpenAI compatibility shims

## Ingress posture
- Private by default
- Narrow ingress only
- First ingress shape is a thin Mini-side library/client.
- The client requires a pre-established Mini-local forwarded endpoint to a
  Studio-local oMLX listener.
- No public routing contract is defined in phase 2.
- No shared adapter service or LAN-visible deployment claim is made in phase 2.

## Primary callable surface
- `POST /v1/chat/completions`
- non-stream only
- exact frozen body fields:
  - `model`
  - `messages`
  - `temperature=0`
  - `top_p=1`
  - `max_tokens`
  - `stream=false`
- exact message shape:
  - two messages only
  - first `system`, second `user`
  - plain string `content` only

Explicitly out of scope in phase 2:
- streaming as a supported callable surface
- tools / `tool_choice`
- structured outputs
- content arrays
- `/v1/responses`

## Observability expectations
- Runtime evidence must emphasize:
  - concurrency behavior
  - prefix/cache reuse behavior
  - cache-tier behavior
  - runtime failure isolation

## Failure policy
- No fallback logic
- No retry policy beyond minimal transport/connect failure surfacing
- Any parse, shape, or upstream HTTP failure is surfaced directly as an adapter
  error or upstream error

## References
- Direct oMLX outperformed the LiteLLM shadow-alias path in the current repo evidence:
  `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`
- Upstream runtime semantics:
  https://github.com/jundot/omlx/blob/main/README.md
