# Service Spec: litellm-orch

## Purpose
OpenAI-compatible gateway for clients. This repo provides routing only and does not
implement inference. It forwards requests to specialist backends (OpenVINO on
the Mini, MLX on the Studio, AFM planned).

## Host & Runtime
- **Host**: Mac mini (Intel i7, 64 GB RAM), Ubuntu 24.04
- **Language/Framework**: Python 3.12, LiteLLM proxy behavior, FastAPI + Uvicorn
- **Inference**: None (upstream only)
- **Bind**: `127.0.0.1:4000` (tailnet HTTPS via Tailscale Serve)

## Endpoints
- `POST /v1/chat/completions` (OpenAI-compatible; forwards to upstream)
- `GET /v1/models` (logical model names from router config)
- `GET /health` (LiteLLM health check across configured deployments)
- `GET /health/readiness` and `GET /health/liveliness` (service readiness/liveness)
- `GET /metrics/` (Prometheus; requires bearer auth; **use trailing slash**)

## Configuration
- Declarative routing in `config/router.yaml` with env-var substitution.
- Environment variables supply upstream base URLs and runtime options.
- Example envs live in `config/env.example`.
- For long-running service use, load env vars explicitly (e.g., systemd `EnvironmentFile=config/env.local`).
- Custom guardrails are declared in `config/router.yaml` under `guardrails`.

## Backends (External Services)
- **OpenVINO LLM server** on the Mini (`http://localhost:9000`, supports `/health`, `/v1/models`, `/v1/chat/completions`)
- **MLX Studio lanes** on the Studio: OpenAI-compatible per-port `vllm-metal` (`vllm serve`)
  endpoints on **8100/8101/8102** (`http://192.168.1.72:<port>/v1`).
- **AFM OpenAI-compatible API** on the Studio (planned; target **9999**)

## Default Logical Models
- `mlx-*` → MLX Studio per-port lanes (`:8100/:8101/:8102`)
- `ov-*` → OpenVINO on `localhost:9000`
- `boost` → Studio OptiLLM proxy on `:4020` (optimization lane)

## Logging (Planned)
- Request logging: JSONL via LiteLLM (`json_logs: true`) for ingestion (model, upstream, latency, status, error).
- Log destination: stdout/journald for now; switch to file output when ingestion pipeline is ready.

## Guardrails
- `transcribe-guardrail` is enabled for `task-transcribe` and `task-transcribe-vivid`.
  It strips wrappers/labels and removes reasoning fields from transcript outputs.
- `harmony-guardrail` is enabled in both `pre_call` and `post_call` for GPT lanes only
  (`deep`, `fast`, `boost`, `boost-deep`):
  - `pre_call`: sanitizes prior `assistant` history turns by extracting Harmony `final`
    content when strict Harmony wire blocks are detected.
  - `post_call`: converts Harmony wire output to `final` only for client-visible response
    content.
  - strict detection guard: no mutation unless real Harmony wire shape is present
    (`<|channel|>` + `<|message|>` + `analysis|final` channel).
  - streaming is pass-through by default; the guardrail does not coerce `stream=false`.
    Clients may still request non-streaming per call.
  - streaming iterator hook currently passes chunks through without post-normalization.
    strict Harmony final-content normalization remains strongest on non-stream responses.
  - Qwen lane (`main`) is passthrough for Harmony normalization.

## Service Management (Planned)
- User systemd service with explicit port binding

## Auth (Current)
- API key enforcement is enabled (bearer auth required for `/v1/*`, `/health`, `/metrics/`).
- Keys are loaded from `config/env.local` by systemd `EnvironmentFile`.

## Orchestration (Planned)
- TinyAgents will be a client of LiteLLM (not a direct backend caller).
- See `docs/tinyagents-integration.md` for IO flow and responsibility split.
