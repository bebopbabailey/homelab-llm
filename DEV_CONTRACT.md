# DEV_CONTRACT — litellm-orch (Mini)

## 1. System Context
* **Host:** Mac mini (Intel Core i7 6-Core, 64GB RAM).
* **OS:** Ubuntu 24.04 Server (Headless/SSH).
* **Network:** LAN + Tailscale access expected.
* **Existing Services (must preserve):**
  * **OLLAMA** on port **11434** (do not modify).
  * **OpenVINO LLM server** (ov-llm-server) on port **9000** (`http://localhost:9000`, backend specialist, external to this repo).
* **MLX OpenAI servers** on Mac Studio (backend specialists) on ports **8100**, **8101**, **8102**, **8103**, **8109** (OpenAI-compatible `/v1/*`).

## 2. Critical Constraints (Non-Negotiable)
* **Do not touch/restart/remove** existing `ollama` service.
* **Dependency management:** Use **uv** only. No global `pip`, no system Python mutations.
* **No driver installs:** Drivers are already installed. Do not add apt installs unless explicitly requested.
* **This repo is routing only:** Do not implement inference here.

## 3. Technical Stack
* **Language:** Python 3.12
* **Gateway:** LiteLLM (proxy/gateway behavior)
* **Web Server:** FastAPI + Uvicorn
* **API Standard:** OpenAI-compatible `/v1/*` for clients.
* **Backends:**
  * **OpenVINO** backend on Mini: `http://localhost:9000` (supports `/health`, `/v1/models`, `/v1/chat/completions`).
* **MLX** backends on Studio: OpenAI-compatible servers on ports **8100**, **8101**, **8102**, **8103**, **8109** (base URLs set via env vars).

## 4. Required Behavior
* Provide a single “front door” OpenAI-compatible endpoint for clients (Aider, tinyagents later).
* Route by logical model name (e.g., `jerry-weak`, `jerry-editor`, `jerry-architect`, `jerry-chat`, `jerry-test`, `lil-jerry`) to upstream backends.
* Expose LiteLLM health endpoints (`/health`, `/health/readiness`, `/health/liveliness`) for scalable monitoring.
* Client-facing model names are plain (`jerry-*`, `lil-jerry`); provider routing stays in `litellm_params.model` (prefixed with `openai/`).
* Initial mapping (config-driven, no hardcoded URLs):
  - `jerry-chat` → MLX `8100`
  - `jerry-weak` → MLX `8103`
  - `jerry-editor` → MLX `8101`
  - `jerry-architect` → MLX `8102`
  - `jerry-test` → MLX `8109`
  - `lil-jerry` → OpenVINO `localhost:9000`
* Keep routing config declarative (YAML + env vars). No hardcoded IPs/ports in Python.

## 5. Definition of Done (for Phase 1)
The system is operational when:
1. A developer can run `uv run ...` and start the gateway on port **4000**.
2. `GET /v1/models` returns the configured logical model names (`jerry-*`, `lil-jerry`).
3. `POST /v1/chat/completions` with `"model": "jerry-weak"` forwards to the MLX `8103` backend and returns a valid OpenAI response.
