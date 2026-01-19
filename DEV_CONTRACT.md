# DEV_CONTRACT — litellm-orch (Mini)

## 1. System Context
* **Host:** Mac mini (Intel Core i7 6-Core, 64GB RAM).
* **OS:** Ubuntu 24.04 Server (Headless/SSH).
* **Network:** LAN + Tailscale access expected.
* **Existing Services (must preserve):**
  * **OLLAMA** on port **11434** (do not modify).
  * **OpenVINO LLM server** (ov-llm-server) on port **9000** (`http://localhost:9000`, backend specialist, external to this repo).
* **MLX OpenAI servers** on Mac Studio (backend specialists) on ports **8100-8119** (team) and **8120-8139** (experimental).

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
* **MLX** backends on Studio: OpenAI-compatible servers on ports **8100-8119** (team) and **8120-8139** (experimental).

## 4. Required Behavior
* Provide a single “front door” OpenAI-compatible endpoint for clients (Aider, tinyagents later).
* Route by logical model name (e.g., `mlx-*`, `ov-*`, `opt-*`) to upstream backends.
* Expose LiteLLM health endpoints (`/health`, `/health/readiness`, `/health/liveliness`) for scalable monitoring.
* Client-facing model names use handles (`mlx-*`, `ov-*`, `opt-*`);
  provider routing stays in `litellm_params.model` with `openai/<base-model>` for OpenAI-compatible backends.
* Initial mapping (config-driven, no hardcoded URLs):
  - `mlx-*` → MLX `8100-8119` (team), `8120-8139` (experimental)
  - `ov-*` → OpenVINO `localhost:9000`
  - `opt-*` → OptiLLM `localhost:4020`
* Keep routing config declarative (YAML + env vars). No hardcoded IPs/ports in Python.

## 5. Definition of Done (for Phase 1)
The system is operational when:
1. A developer can run `uv run ...` and start the gateway on port **4000**.
2. `GET /v1/models` returns the configured logical model names (`mlx-*`, `ov-*`, `opt-*`).
3. `POST /v1/chat/completions` with `"model": "mlx-qwen2-5-coder-32b-instruct-8bit"` forwards to the MLX `8103` backend and returns a valid OpenAI response.
