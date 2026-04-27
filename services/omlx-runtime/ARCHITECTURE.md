# Architecture: omlx-runtime

## Role
- Represent the specialized runtime plane as a first-class service boundary.
- Keep oMLX separate from the commodity inference plane.

## Placement
- Host: Studio
- Plane: specialized runtime
- Relationship to the commodity plane:
  - may be consumed later by thin adapters or orchestration
  - is not modeled as a public gateway backend in phase 1

## First ingress shape
- The first ingress is a Mini-side library/client, not a Mini-side middlebox.
- The client talks to a pre-established Mini-local forwarded endpoint that
  targets a Studio-local oMLX listener.
- The client preserves the direct request shape and surfaces errors without
  fallback or provider normalization.

## Boundaries
- `omlx-runtime` does not redefine LiteLLM.
- `omlx-runtime` does not replace OpenHands sandboxes.
- `omlx-runtime` does not imply Open WebUI compatibility.
- `omlx-runtime` is allowed to preserve runtime-specific behavior rather than
  flattening it into a generic alias contract.
- `omlx-runtime` phase 2 is not a generic OpenAI compatibility project.
