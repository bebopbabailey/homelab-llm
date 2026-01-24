# TASKS — litellm-orch (Mini) Phased Plan

## Phase 0 — Repo Bootstrapping (this commit)
- [x] uv project initialized (Python 3.12, venv in-repo)
- [x] dependencies installed & pinned; `uv.lock` committed
- [x] directory skeleton created: `config/ scripts/ logs/ docs/`
- [x] `DEV_CONTRACT.md` and `TASKS.md` present
- [x] create `AGENTS.md` file

## Phase 1 — Minimal Gateway (Single Endpoint, Static Model Map)
Goal: Start a single OpenAI-compatible gateway on the Mini that routes to upstream endpoints.

- [x] Choose gateway approach:
  - [x] Use LiteLLM’s proxy mode if compatible with pinned deps
  - [ ] If proxy extras conflict, wrap LiteLLM routing via a minimal FastAPI forwarder (no business logic beyond mapping + proxying)
- [x] Create `config/env.example`
- [x] Create `config/router.yaml` containing:
  - [x] logical model names (`mlx-*`, `ov-*`)
  - [x] upstream base URLs (env-var substituted; MLX ports 8100-8119 team, 8120-8139 experimental; OpenVINO on localhost:9000)
  - [x] upstream “model id” mapping if needed
- [x] Document minimal runbook in `README.md`
- [x] Create `scripts/run-dev.sh` to run locally in foreground
- [x] Create `scripts/smoke-test.sh`:
  - [x] `/v1/models` returns logical names
  - [x] `/v1/chat/completions` routes and returns response

## Phase 2 — Aider Integration (3 Roles)
Goal: Aider on any device points at the Mini gateway and uses 3 roles.

- [x] Create Aider usage doc (no installation here; clients install Aider separately)
- [x] Define the Aider model role mapping:
  - [x] weak model → `mlx-qwen2-5-coder-32b-instruct-8bit`
  - [x] editor model → `mlx-deepseek-r1-distill-llama-70b-8bit`
  - [x] main model → `mlx-gpt-oss-120b-6bit-gs64`
  - [x] architect uses Aider's architect mode (edit format), not a separate model
- [x] Validate end-to-end from a non-mini machine over LAN and over Tailscale

## Phase 3 — Backends & Health Awareness
Goal: Make routing resilient but still boring.

- [x] Add health checks for backends
  - [x] OpenVINO: `/health`
  - [x] MLX: cheap `/v1/chat/completions` probe (preferred over `/v1/models`)
  - [x] Prefer LiteLLM `/health` endpoints for scalable aggregation across configured deployments
- [ ] Add simple failure behavior:
  - [x] clear error response if upstream down (LiteLLM default + retry/cooldown configured)
  - [ ] optional fallback mapping (config-driven; defer until standard model lineup)
- [x] Add request logging (JSON): model name, upstream, latency, status, error
- [ ] Add AFM backend (Studio) once API base URL + model IDs are confirmed

## Phase 4 — Service Hardening (Boot + Security)
Goal: Make it long-running and safe.

- [ ] bind to 0.0.0.0 with explicit port (avoid conflicts with 9000 and 11434)
- [ ] systemd user service for the gateway (with linger enabled as needed)
- [x] document API key enforcement (single key) and how clients set it; enable later as needed
- [x] tighten firewall/tailscale exposure notes in `docs/security.md`
- [x] remove duplicate `openai/` aliases from LiteLLM model list
- [ ] decide log destination for ingestion pipeline (keep stdout/journald for now; switch to file if/when needed)
  - [ ] defer until ingestion pipeline is defined (current: stdout/journald)
- [ ] Studio launchd: boot ensemble pending new 5-model MLX set

## Phase 5 — Orchestrator Hooks (tinyagents-ready)
Goal: Keep gateway tool-agnostic but orchestration-friendly.

- [ ] Add a minimal “admin” interface for status (read-only)
- [ ] Optional: allow the orchestrator to switch routing profiles (config sets)
- [ ] Ensure all changes remain config-driven and reversible
- [x] Add model-level prompt injection via LiteLLM callbacks (no per-request prompt_id)

## Nice to Haves
- [ ] Add a helper script to detect or extract MLX chat templates and launch MLX servers with `--chat-template-file` automatically (durable model swaps).
- [ ] Fork `mlx-openai-server` and apply a permanent BatchEncoding→input_ids fix; point `/opt/mlx-launch` to the fork.
- [ ] Add tag/capability metadata for health output (compact JSON enrichment).
- [ ] Add a lightweight routing rule to force short/low‑complexity prompts (e.g., transcript cleaning) to `none` to avoid heavy OptiLLM techniques.
