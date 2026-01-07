# 00-EXTRACTION_MAP

## Key artifacts scanned
- Repo: `/home/christopherbailey/litellm-orch`
  - `/home/christopherbailey/litellm-orch/config/router.yaml`
  - `/home/christopherbailey/litellm-orch/config/env.local`
  - `/home/christopherbailey/litellm-orch/config/env.example`
  - `/home/christopherbailey/litellm-orch/README.md`
  - `/home/christopherbailey/litellm-orch/DEV_CONTRACT.md`
  - `/home/christopherbailey/litellm-orch/SERVICE_SPEC.md`
  - `/home/christopherbailey/litellm-orch/ARCHITECTURE.md`
  - `/home/christopherbailey/litellm-orch/docs/openwebui.md`
  - `/home/christopherbailey/litellm-orch/docs/security.md`
  - `/home/christopherbailey/litellm-orch/docs/tinyagents-integration.md`
  - `/home/christopherbailey/litellm-orch/scripts/run-dev.sh`
  - `/home/christopherbailey/litellm-orch/scripts/health-check.sh`
  - `/home/christopherbailey/litellm-orch/scripts/run-mlx-studio.sh`
  - `/home/christopherbailey/litellm-orch/scripts/run-mlx-gptoss-architect.sh`
- Repo: `/home/christopherbailey/ov-llm-server`
  - `/home/christopherbailey/ov-llm-server/main.py`
  - `/home/christopherbailey/ov-llm-server/README.md`
  - `/home/christopherbailey/ov-llm-server/ov-server.service`
  - `/home/christopherbailey/ov-llm-server/ov-server.env`
- Install dir: `/home/christopherbailey/open-webui` (venv + secret key file)
- Systemd + env:
  - `/etc/systemd/system/litellm-orch.service`
  - `/etc/systemd/system/open-webui.service`
  - `/etc/open-webui/env`
  - `/home/christopherbailey/.config/systemd/user/ov-server.service`
  - `/home/christopherbailey/.config/ov-llm-server/ov-server.env`
  - `/etc/systemd/system/ollama.service`
  - `/etc/systemd/system/ollama.service.d/override.conf`
- Host/network evidence:
  - `/home/christopherbailey/.ssh/config`
  - `/proc/net/fib_trie`

## Facts extracted (evidence-based)
- LiteLLM proxy runs via systemd on port 4000 and binds to 0.0.0.0.
  Evidence: `/etc/systemd/system/litellm-orch.service`
  Snippet:
  ```
  EnvironmentFile=/home/christopherbailey/litellm-orch/config/env.local
  ExecStart=/home/christopherbailey/.local/bin/uv run litellm --config /home/christopherbailey/litellm-orch/config/router.yaml --host 0.0.0.0 --port 4000
  ```
- LiteLLM routing config uses env-var substitution for upstream model names, base URLs, and API keys.
  Evidence: `/home/christopherbailey/litellm-orch/config/router.yaml`
  Snippet:
  ```
  - model_name: jerry-weak
    litellm_params:
      model: os.environ/JERRY_WEAK_MODEL
      api_base: os.environ/JERRY_WEAK_API_BASE
      api_key: os.environ/JERRY_WEAK_API_KEY
  ```
- Active upstream base URLs point to Studio MLX ports and local OpenVINO.
  Evidence: `/home/christopherbailey/litellm-orch/config/env.local`
  Snippet:
  ```
  JERRY_CHAT_API_BASE=http://192.168.1.72:8100/v1
  JERRY_EDITOR_API_BASE=http://192.168.1.72:8101/v1
  JERRY_ARCHITECT_API_BASE=http://192.168.1.72:8102/v1
  JERRY_WEAK_API_BASE=http://192.168.1.72:8103/v1
  JERRY_TEST_API_BASE=http://192.168.1.72:8109/v1
  LIL_JERRY_API_BASE=http://localhost:9000/v1
  ```
- Open WebUI runs via systemd on port 3000 bound to 0.0.0.0 and loads /etc/open-webui/env.
  Evidence: `/etc/systemd/system/open-webui.service`
  Snippet:
  ```
  EnvironmentFile=/etc/open-webui/env
  ExecStart=/home/christopherbailey/open-webui/.venv/bin/open-webui serve --host 0.0.0.0 --port 3000
  ```
- Open WebUI system service is enabled and active; user service removed.
  Evidence: `systemctl is-enabled open-webui.service`, `systemctl is-active open-webui.service`
- Open WebUI is configured to call LiteLLM at 127.0.0.1:4000/v1.
  Evidence: `/etc/open-webui/env`
  Snippet:
  ```
  OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1
  OPENAI_API_KEY=dummy
  ```
- Open WebUI `/health` responds on port 3000.
  Evidence: `curl http://127.0.0.1:3000/health`
  Snippet:
  ```
  {"status":true}
  ```
- Mini LAN IP and Tailscale IP observed via `/proc/net/fib_trie`.
  Evidence: `/proc/net/fib_trie`
  Snippet:
  ```
  |-- 192.168.1.71
  |-- 100.69.99.60
  ```
- SSH aliases for `studio` and `hp` are defined in user SSH config.
  Evidence: `/home/christopherbailey/.ssh/config`
  Snippet:
  ```
  Host studio
      HostName 192.168.1.72
  Host hp
      HostName 192.168.1.70
  ```
- OpenVINO backend runs via user systemd on port 9000 bound to 0.0.0.0.
  Evidence: `/home/christopherbailey/.config/systemd/user/ov-server.service`
  Snippet:
  ```
  EnvironmentFile=/home/christopherbailey/.config/ov-llm-server/ov-server.env
  ExecStart=/home/christopherbailey/.local/bin/uv run uvicorn main:app --host 0.0.0.0 --port 9000 --workers 1
  ```
- OpenVINO backend exposes /health, /v1/models, and /v1/chat/completions.
  Evidence: `/home/christopherbailey/ov-llm-server/main.py`
  Snippet:
  ```
  @app.get("/health")
  @app.get("/v1/models")
  @app.post("/v1/chat/completions")
  ```
- MLX OpenAI servers are launched by scripts with host 0.0.0.0 and ports 8100/8101/8102/8103/8109.
  Evidence: `/home/christopherbailey/litellm-orch/scripts/run-mlx-studio.sh`, `/home/christopherbailey/litellm-orch/scripts/run-mlx-gptoss-architect.sh`, `/home/christopherbailey/litellm-orch/scripts/run-mlx-test-model.sh`
  Snippet:
  ```
  --host 0.0.0.0 --port 8103
  --host 0.0.0.0 --port 8101
  --host 0.0.0.0 --port 8102
  --host 0.0.0.0 --port 8100
  --host 0.0.0.0 --port 8109
  ```
- Studio launchd plist exists and MLX runtime directory is present.
  Evidence: `ssh thestudio@192.168.1.72`
  Snippet:
  ```
  /Library/LaunchDaemons/com.bebop.mlx-launch.plist
  /opt/mlx-launch
  ```
- Ollama is installed as a systemd service and bound to 0.0.0.0:11434.
  Evidence: `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf`
  Snippet:
  ```
  ExecStart=/usr/local/bin/ollama serve
  Environment="OLLAMA_HOST=0.0.0.0:11434"
  ```

## Conflicts found
- OpenVINO bind scope conflict: docs claim localhost-only, but the systemd unit binds 0.0.0.0.
  Evidence: `/home/christopherbailey/litellm-orch/docs/security.md` vs `/home/christopherbailey/.config/systemd/user/ov-server.service`
  Recommendation: treat the systemd unit as source of truth for exposure until the doc is updated.
- Open WebUI system unit is enabled/active; user unit removed to prevent conflicts.
  Evidence: `/etc/systemd/system/open-webui.service`, `systemctl is-enabled open-webui.service`, `systemctl is-active open-webui.service`
  Recommendation: keep system unit as source of truth.
- OpenVINO env mismatch: repo env uses fp16 model path, active env file uses fp32.
  Evidence: `/home/christopherbailey/ov-llm-server/ov-server.env` vs `/home/christopherbailey/.config/ov-llm-server/ov-server.env`
  Recommendation: treat the active env file as source of truth for runtime.
- MLX port list mismatch: AGENTS.md lists only 8100-8102, while env and docs include 8103 and 8109.
  Evidence: `/home/christopherbailey/litellm-orch/AGENTS.md` vs `/home/christopherbailey/litellm-orch/config/env.local` and `/home/christopherbailey/litellm-orch/SERVICE_SPEC.md`
  Recommendation: treat env.local and router config as source of truth for routing.
- TinyAgents base URL in docs differs from active env patterns.
  Evidence: `/home/christopherbailey/litellm-orch/docs/tinyagents-integration.md` references `http://192.168.1.71:4000`
  Recommendation: verify the Mini LAN IP and update the doc if needed.

## Missing expected artifacts (UNVERIFIED)
- Repo `/home/christopherbailey/OpenVINO` (expected per instructions) was not found; active backend repo appears to be `/home/christopherbailey/ov-llm-server`.
- Open WebUI repo content or compose files were expected but only `/home/christopherbailey/open-webui` (venv + secret key) exists.
