# Voice Gateway — ARCHITECTURE

## Why This Exists
The platform already supports text interaction elsewhere. Voice Gateway Phase 1
adds the smallest durable audio slice while preserving platform constraints:

- XTTS-v2 is intended to run locally on the Orin.
- Phase 1 remains local-first and localhost-only.
- Later STT and LiteLLM integration can layer on top of the same package.

## Current Status
- Orin is the designated Voice Gateway host.
- A live Voice Gateway deployment is not documented yet.
- The current scaffold remains provisional until a repo-tracked container build
  succeeds on Orin and the XTTS import gate passes inside that runtime.

## Phase 1 Topology
- **Orin** hosts the Voice Gateway Phase 1 runtime.
- The active recovery path packages the XTTS runtime and the localhost-only
  wrapper together in a repo-built container.
- No Mini caller is required for Phase 1.
- No LAN bind is part of the Phase 1 contract.

## Phase 1 Data Flow
1) Operator provides text locally
2) Voice Gateway discovers built-in XTTS speakers
3) XTTS-v2 synthesizes WAV output
4) CLI optionally plays the WAV locally
5) HTTP wrapper, when used, returns the WAV over localhost only

## Boundary Rules
- Voice Gateway remains in the Interface layer.
- Phase 1 does not call LiteLLM or any inference backend directly.
- Phase 1 does not implement STT.
- The engine/runtime packaging choice must not change the HTTP or CLI contract.

## Component Diagram (Phase 1)
[Text input] → (Voice Gateway)
  ├─ built-in speaker discovery
  ├─ XTTS-v2 engine
  ├─ WAV output
  └─ optional local playback

## Degradation Strategy
- If XTTS dependencies are unavailable: fail fast with a documented preflight error.
- If built-in speaker discovery fails: readiness fails and synth calls return deterministic errors.
- If playback fails: keep the generated WAV and report playback failure separately.
- If bootstrap is not proven on Orin: stop feature work and recover packaging/docs first.

## Observability
Voice Gateway logs structured timing for discovery, model load, synthesis, WAV
write, and optional playback so later phases can extend the same log contract.

## Security / Exposure
- Phase 1 HTTP binds to `127.0.0.1` only.
- No LAN or public exposure is introduced in Phase 1.
- No model download should be triggered during bootstrap validation.

## Later Phases
- STT
- LiteLLM orchestration
- Mini-to-Orin callers
- cloned voice enrollment
