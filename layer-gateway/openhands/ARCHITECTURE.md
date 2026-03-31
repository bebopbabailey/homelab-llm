# Architecture: OpenHands (Mini Phase A)

OpenHands Phase A is a thin managed operator loop:

1. `openhands.service` starts the OpenHands app container on the Mini.
2. The app publishes a localhost-only UI on `127.0.0.1:4031`.
3. Tailscale Serve maps `svc:hands` to that loopback listener for tailnet-only operator access.
4. The app uses the host Docker daemon to create sandbox containers for task work.
5. Only a disposable host workspace is mounted into the sandbox as `/workspace`.
6. The operator enters a temporary provider/API key directly in the UI.
7. The worker performs a small local coding task in the scratch workspace.

This is now part of the always-on homelab runtime only as a supervised Phase A
UI baseline. It remains a local, reversible proving ground for:

- sandbox mechanics
- approval flow
- diff review
- validation loop
- operator trust-building

Phase B preserves this shape and changes only the model-provider boundary to
LiteLLM.
