# litellm-orch

OpenAI-compatible gateway that forwards requests to external LLM backends. This repo
provides routing only and does not implement inference.

## Scope
- Gateway only; no inference in this repo.
- Declarative routing via `config/router.yaml` with env-var substitution.
- Logical model names use base model names (kebab-case). MLX models are prefixed with `mlx-`.

## Backends (External Services)
- MLX `vllm-metal` lanes on the Studio: `mlx-*` (ports `8100-8119` team; `8120-8139` experimental).
- OpenVINO LLM server on the Mini (external to this repo) is not wired into LiteLLM
  right now.

## Configuration
- `config/router.yaml` maps logical model names to upstream endpoints.
- `config/env.example` provides the env var template for base URLs and model IDs.
- Copy `config/env.example` to `config/env.local` (git-ignored) and set real IPs/model IDs.
- For long-running service use, load env vars explicitly (e.g., systemd `EnvironmentFile=config/env.local`).
- For OpenAI-compatible upstreams, keep the handle as the alias and set `litellm_params.model` to `openai/<base-model>`.

## Aider
- See `AIDER.md` for a 3-model setup (main/editor/weak) via the LiteLLM proxy.

## Run (LiteLLM Proxy)
- Ensure `config/env.local` is populated and loaded into the environment.
- Run the proxy (example command):
  - `uv run litellm --config config/router.yaml --port 4000`
 - Helper script (Mini): `scripts/run-dev.sh`
 - Optional alias: `scripts/run-dev-chat.sh` (same config; kept for convenience)

## Studio MLX Control
- Use `platform/ops/scripts/mlxctl` (registry-aware, stable aliases for ports 8100-8139).
- After MLX port changes, run `mlxctl sync-gateway` to refresh router/env/handles.
- Legacy MLX helper scripts were removed to reduce drift.

## Verify
- `GET /v1/models` returns `mlx-*` handles from the router config.
- `POST /v1/chat/completions` with a known `mlx-*` model returns a valid response.
- `GET /health/readiness` is the default health signal (fast, no deep probes).
- `GET /health` is a deep probe and can show unhealthy when backends are offline.

## OptiLLM coding aliases
- `boost-plan`: deterministic `plansearch` profile over deep lane.
- `boost-plan-verify`: deterministic `self_consistency` verifier over deep lane.
- `boost-ideate`: deterministic `moa` profile over deep lane.
- `boost-fastdraft`: deterministic `bon` profile over fast lane.

## Health Check Script
- `scripts/health-check.sh` outputs compact, pretty-printed JSON from LiteLLM `/health`.
- Set `VERBOSE=1` to print the raw LiteLLM health payload.

## Notes
- Immediate goals: stable LiteLLM proxy routing plus a 3-model Aider setup (see `AIDER.md`).
- `AGENTS.md` provides contributor guidelines for this repo.
- Known issues and workarounds are tracked in `docs/known-issues.md`.
- Security and exposure notes are in `docs/security.md`.
- Open WebUI setup (non-docker) for the Mini is documented in `docs/openwebui.md`.
- TinyAgents integration notes (planned) live in `docs/tinyagents-integration.md`.

## Auth (Planned)
- API key enforcement will be enabled later when non-local access is needed.
- LiteLLM supports API key management and request auth without custom code.
- When ready, set a proxy key and require it on requests:
  - `export LITELLM_PROXY_KEY="your-strong-key"`
  - Clients send `Authorization: Bearer <key>`.
