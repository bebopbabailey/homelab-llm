# litellm-orch

OpenAI-compatible gateway that forwards requests to external LLM backends. This repo
provides routing only and does not implement inference.

## Scope
- Gateway only; no inference in this repo.
- Declarative routing via `config/router.yaml` with env-var substitution.
- Logical model names (canonical): `openai/jerry-weak`, `openai/jerry-editor`, `openai/jerry-architect`, `openai/lil-jerry`, `openai/jerry-chat`.

## Model Naming Standard
- Canonical client-facing names MUST use the `openai/` prefix (e.g., `openai/jerry-architect`).
- Plain-name aliases (`jerry-*`) are temporary compatibility shims and will be removed once all clients are updated.

## Backends (External Services)
- MLX OpenAI servers on the Studio: `jerry-chat` on `8100`, `jerry-editor` on `8101`, `jerry-architect` on `8102`, `jerry-weak` on `8103`.
- OpenVINO LLM server on the Mini (external to this repo), mapped as `openai/lil-jerry`.

## Configuration
- `config/router.yaml` maps logical model names to upstream endpoints.
- `config/env.example` provides the env var template for base URLs and model IDs.
- Copy `config/env.example` to `config/env.local` (git-ignored) and set real IPs/model IDs.
- For long-running service use, load env vars explicitly (e.g., systemd `EnvironmentFile=config/env.local`).

## Aider
- See `AIDER.md` for a 3-model setup (main/editor/weak) via the LiteLLM proxy.

## Run (LiteLLM Proxy)
- Ensure `config/env.local` is populated and loaded into the environment.
- Run the proxy (example command):
  - `uv run litellm --config config/router.yaml --port 4000`
 - Helper script (Mini): `scripts/run-dev.sh`
 - Optional alias: `scripts/run-dev-chat.sh` (same config; kept for convenience)

## Studio MLX Helpers
- `scripts/run-mlx-studio.sh` starts the three coding models on ports `8103`, `8101`, `8102`.
- `scripts/stop-mlx-studio.sh` stops the MLX servers by port.
- `scripts/run-mlx-gptoss-architect.sh` starts GPT-OSS 120B on port `8100` as `jerry-chat`.

## Verify
- `GET /v1/models` returns `openai/jerry-*` and `openai/lil-jerry`.
- `POST /v1/chat/completions` with `"model": "openai/jerry-weak"` returns a valid response.
- `GET /health` returns LiteLLM health results for configured deployments.

## Health Check Script
- `scripts/health-check.sh` outputs compact, pretty-printed JSON from LiteLLM `/health`.
- Set `VERBOSE=1` to print the raw LiteLLM health payload.

## Notes
- Immediate goals: stable LiteLLM proxy routing plus a 3-model Aider setup (see `AIDER.md`).
- `AGENTS.md` provides contributor guidelines for this repo.
- Known issues and workarounds are tracked in `docs/known-issues.md`.
- Security and exposure notes are in `docs/security.md`.
- Open WebUI setup (non-docker) for the Mini is documented in `docs/openwebui.md`.

## Auth (Planned)
- API key enforcement will be enabled later when non-local access is needed.
- LiteLLM supports API key management and request auth without custom code.
- When ready, set a proxy key and require it on requests:
  - `export LITELLM_PROXY_KEY="your-strong-key"`
  - Clients send `Authorization: Bearer <key>`.
