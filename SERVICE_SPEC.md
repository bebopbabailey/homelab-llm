# Service Spec: litellm-orch

## Purpose
OpenAI-compatible gateway for clients. This repo provides routing only and does not
implement inference. It forwards requests to specialist backends (e.g., OpenVINO on
the Mini and MLX on the Studio).

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

## Backends (External Services)
- **OpenVINO LLM server** on the Mini (`http://localhost:9000`, supports `/health`, `/v1/models`, `/v1/chat/completions`)
- **MLX OpenAI servers** on the Studio: `jerry-chat` **8100**, `jerry-editor` **8101**, `jerry-architect` **8102**, `jerry-weak` **8103**, test model **8109** (OpenAI-compatible `/v1/*`)

## Default Logical Models
- `jerry-chat` → MLX `8100`
- `jerry-weak` → MLX `8103`
- `jerry-editor` → MLX `8101`
- `jerry-architect` → MLX `8102`
- `jerry-test` → MLX `8109`
- `lil-jerry` → OpenVINO on `localhost:9000`

## Logging (Planned)
- Request logging: JSONL via LiteLLM (`json_logs: true`) for ingestion (model, upstream, latency, status, error).
- Log destination: stdout/journald for now; switch to file output when ingestion pipeline is ready.

## Service Management (Planned)
- User systemd service with explicit port binding

## Auth (Planned)
- API key enforcement will be enabled once non-local access is required.
- Proposed approach: set `LITELLM_PROXY_KEY` and require `Authorization: Bearer <key>` from clients.

## Orchestration (Planned)
- TinyAgents will be a client of LiteLLM (not a direct backend caller).
- See `docs/tinyagents-integration.md` for IO flow and responsibility split.
