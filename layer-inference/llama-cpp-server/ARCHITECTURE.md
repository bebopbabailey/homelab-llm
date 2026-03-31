# Architecture: llama-cpp-server

## Role
This service boundary codifies the repo-owned GPT serving family for `fast` and
`deep` while keeping public clients behind LiteLLM.

## Runtime shape
- Runtime family: `llmster` headless daemon on the Studio
- Inference architecture: llama.cpp
- Canonical shared listener: `192.168.1.72:8126`
- Raw mirrors: `127.0.0.1:8130` and `127.0.0.1:8131` for diagnostic truth-path
  probes only

## Ownership boundary
- This service owns the direct GPT backend contract for `fast` and `deep`.
- LiteLLM owns the client-facing alias surface, auth, routing, retries, and
  observability.
- Public clients must not call the Studio listener directly.

## Model posture
- `fast` maps to the shared `llmster-gpt-oss-20b-mxfp4-gguf` lane.
- `deep` maps to the shared `llmster-gpt-oss-120b-mxfp4-gguf` lane.
- The internal OpenHands worker alias `code-reasoning` inherits the same GPT
  backend behavior through LiteLLM by following `deep`.

## Formatting and tool-calling
- GPT formatting ownership is upstream-first at this boundary.
- Accepted direct responses on the current `llmster` path are already the
  canonical formatting truth for `fast` and `deep`.
- Named/object-form forced-tool choice is still unsupported on the current
  backend family and remains out of contract.
- Strict structured-output guarantees are not part of the supported GPT
  contract.

## Non-goals
- Replacing `main`
- Exposing direct Studio client paths
- Treating raw `llama-server` mirrors as the public runtime
