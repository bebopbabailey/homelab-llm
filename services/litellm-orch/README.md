# litellm-orch

OpenAI-compatible gateway that forwards requests to external backends. This
service owns routing, auth, retries, fallbacks, and generic tool/search proxying
only; it does not implement inference.

## Scope
- Gateway only; no inference in this repo.
- Declarative routing via `config/router.yaml` with env-var substitution.
- Logical handles use stable client-facing names; upstream OpenAI-compatible
  backends use `openai/<base-model>` in `litellm_params.model`.

## Runtime Contract
- Bind: `0.0.0.0:4000`
- On-host callers may keep using `127.0.0.1:4000`
- Canonical Studio upstream path: `http://192.168.1.71:4000/v1`
- Auth: API key enforcement is active for `/v1/*` and `/health`
- Open `/health/readiness`, `/health/liveliness`, and `/metrics/` remain part of
  the current runtime contract

## Backends
- MLX `vllm-metal` lanes on the Studio: `deep`, `main`, and `fast`
- `task-transcribe` and `task-transcribe-vivid` reuse the same `8101` MLX lane
  as text-cleanup aliases
- Voice Gateway on the Orin for speech aliases
- SearXNG on the Mini for generic search tooling

## OpenCode Note
- Repo-local OpenCode defaults and agent/skill behavior are documented in
  `/home/christopherbailey/homelab-llm/docs/OPENCODE.md`.
- The local canonical public LLM trio remains `fast`, `main`, and `deep`.
- Human-chat traffic is Chat Completions-first through LiteLLM for `main`,
  `deep`, `fast`, and the experimental `chatgpt-5` lane.
- `chatgpt-5` now routes through the Mini-local `ccproxy-api` Codex sidecar.
- `task-transcribe` and `task-transcribe-vivid` are additional task aliases,
  not part of the public human chat-lane trio.
- `task-json` is an additional utility alias, not part of the public human
  chat-lane trio.

## Configuration
- `config/router.yaml` maps logical handles to upstream endpoints.
- `config/env.example` provides the non-secret env template.
- `config/env.local` is git-ignored and remains the runtime env source for
  long-running service use.
- For Studio team lanes (`8100-8119`), use `platform/ops/scripts/mlxctl` and
  `mlxctl sync-gateway` as the source of truth flow.

## Verification
- `GET /v1/models` returns the expected logical handles from `config/router.yaml`
- `GET /health/readiness` is the default fast health signal
- `GET /health` is a deeper probe and may report unhealthy when backends are offline

## Supporting Docs
- `SERVICE_SPEC.md` for endpoint/auth/runtime details
- `RUNBOOK.md` for health checks and restart boundaries
- `CONSTRAINTS.md` for non-negotiables
