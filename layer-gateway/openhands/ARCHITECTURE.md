# Architecture: OpenHands (Mini Phase A)

OpenHands Phase A is a thin local operator loop:

1. The operator launches the OpenHands app container on the Mini.
2. The app publishes a localhost-only UI on `127.0.0.1:4031`.
3. The app uses the host Docker daemon to create sandbox containers for task work.
4. Only a disposable host workspace is mounted into the sandbox as `/workspace`.
5. The operator enters a temporary provider/API key directly in the UI.
6. The worker performs a small local coding task in the scratch workspace.

This is intentionally not part of the always-on homelab runtime. It is a
local, reversible proving ground for:

- sandbox mechanics
- approval flow
- diff review
- validation loop
- operator trust-building

Phase B preserves this shape and changes only the model-provider boundary to
LiteLLM.
