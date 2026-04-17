# Service Spec: qwen-agent-proxy

## Purpose
Experimental host-local Qwen-Agent sidecar for Qwen3-Coder-Next-backed
coding-agent tool use on the Mini.

## Host & Runtime
- Host: Mini
- Runtime: Python CLI (`uv` + `uvicorn`)
- Bind:
  - default operator path: `127.0.0.1:4021`
  - Docker-bridge path when OpenHands must reach it: `172.17.0.1:4021`
- Exposure: host-local only; never bind to LAN interfaces
- Systemd unit: `qwen-agent-proxy.service`

## Endpoints
- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

## Auth
- Local bearer token via `/etc/homelab-llm/qwen-agent-proxy.secret.env`
- Backend auth to Studio `8134` remains `dummy` / none on the current local path

## Current Contract
- Intended downstream consumers: direct OpenHands shadow provider path, shadow
  LiteLLM experiments, and direct operator probes
- Supported tool modes in this slice:
  - `auto`
  - `required`
  - named function choice
- Unsupported in this slice:
  - streaming
  - `/v1/responses`
- Default shadow model id: `qwen-agent-coder-next-shadow`
- Default backend target: `http://127.0.0.1:18134/v1` via local SSH tunnel to
  the Studio `8134` shadow lane

## Notes
- `qwen-agent==0.0.34` is pinned for this lane.
- `use_raw_api` remains configurable but defaults to `false`.
- The service fails closed when `required` or named tool choice does not yield a
  callable function object.
