# Service Spec: litellm-orch

## Purpose
OpenAI-compatible gateway for clients. This repo provides routing only and does not
implement inference. It forwards requests to specialist backends (OpenVINO on
the Mini, MLX on the Studio, AFM planned).

## Host & Runtime
- **Host**: Mac mini (Intel i7, 64 GB RAM), Ubuntu 24.04
- **Language/Framework**: Python 3.12, LiteLLM proxy behavior, FastAPI + Uvicorn
- **Inference**: None (upstream only)

## Endpoints
- `POST /v1/chat/completions` (OpenAI-compatible; forwards to upstream)
- `GET /v1/models` (logical model names from router config)
- `GET /health` (LiteLLM health check across configured deployments)
- `GET /health/readiness` and `GET /health/liveliness` (service readiness/liveness)

## Configuration
- Declarative routing in `config/router.yaml` with env-var substitution.
- Environment variables supply upstream base URLs and runtime options.
- Example envs live in `config/env.example`.
- For long-running service use, load env vars explicitly (e.g., systemd `EnvironmentFile=config/env.local`).
- Custom guardrails are declared in `config/router.yaml` under `guardrails`.

## Backends (External Services)
- **OpenVINO LLM server** on the Mini (`http://localhost:9000`, supports `/health`, `/v1/models`, `/v1/chat/completions`)
- **MLX OpenAI servers** on the Studio: ports **8100-8119** (team) and **8120-8139** (experimental)
- **AFM OpenAI-compatible API** on the Studio (planned; target **9999**)

## Default Logical Models
- `mlx-*` → MLX ports `8100-8119` (team), `8120-8139` (experimental)
- `ov-*` → OpenVINO on `localhost:9000`
- `mlx-*` may be routed through OptiLLM on `localhost:4020`

## Logging (Planned)
- Request logging: JSONL via LiteLLM (`json_logs: true`) for ingestion (model, upstream, latency, status, error).
- Log destination: stdout/journald for now; switch to file output when ingestion pipeline is ready.

## Guardrails
- `promptopt-max-guardrail` post-call guardrail implements fan-out → reducer → cleanup for `p-opt-max`.
- Guardrail code: `config/promptopt_guardrail.py`.

## Service Management (Planned)
- User systemd service with explicit port binding

## Auth (Planned)
- API key enforcement will be enabled once non-local access is required.
- Proposed approach: set `LITELLM_PROXY_KEY` and require `Authorization: Bearer <key>` from clients.

## Orchestration (Planned)
- TinyAgents will be a client of LiteLLM (not a direct backend caller).
- See `docs/tinyagents-integration.md` for IO flow and responsibility split.
