# 03-SERVICE_INVENTORY

## LiteLLM proxy (litellm-orch)
- Purpose: OpenAI-compatible gateway that routes to upstream backends; no inference.
- Owner repo: `/home/christopherbailey/litellm-orch`
- Launch: systemd unit `/etc/systemd/system/litellm-orch.service`
- Restart policy: `Restart=always`, `RestartSec=2`
- Logs: journald (systemd); JSON logs enabled via `litellm_settings.json_logs`.
- Dependencies: `/home/christopherbailey/litellm-orch/config/env.local`, `/home/christopherbailey/litellm-orch/config/router.yaml`, upstream base URLs.
- Evidence:
  ```
  ExecStart=/home/christopherbailey/.local/bin/uv run litellm --config /home/christopherbailey/litellm-orch/config/router.yaml --host 0.0.0.0 --port 4000
  ```
  ```
  litellm_settings:
    json_logs: true
  ```

## Open WebUI
- Purpose: Local chat UI that calls LiteLLM via OpenAI-compatible API.
- Owner repo: installed at `/home/christopherbailey/open-webui` (no repo source found here).
- Launch: systemd unit `/etc/systemd/system/open-webui.service` (system, enabled and active). User unit removed per policy to avoid conflicts.
- Restart policy: `Restart=always`, `RestartSec=3`
- Logs: journald (systemd).
- Data/secret locations: `/home/christopherbailey/.open-webui` (DATA_DIR), `/home/christopherbailey/open-webui/.webui_secret_key`.
- Dependencies: `/etc/open-webui/env` (system service).
- Evidence:
  ```
  ExecStart=/home/christopherbailey/open-webui/.venv/bin/open-webui serve --host 0.0.0.0 --port 3000
  ```
  ```
  OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1
  ```
  ```
  DATA_DIR=/home/christopherbailey/.open-webui
  ```

## OpenVINO LLM server (ov-llm-server)
- Purpose: OpenAI-compatible chat backend for local OpenVINO models.
- Owner repo: `/home/christopherbailey/ov-llm-server`
- Launch: user systemd unit `/home/christopherbailey/.config/systemd/user/ov-server.service`
- Restart policy: `Restart=on-failure`, `RestartSec=3`
- Logs: user journald (`journalctl --user -u ov-server.service`).
- Dependencies: `/home/christopherbailey/.config/ov-llm-server/ov-server.env`, model registry at `/home/christopherbailey/models/converted_models/registry.json`.
- Evidence:
  ```
  ExecStart=/home/christopherbailey/.local/bin/uv run uvicorn main:app --host 0.0.0.0 --port 9000 --workers 1
  ```
  ```
  OV_REGISTRY_PATH=/home/christopherbailey/models/converted_models/registry.json
  ```

## MLX OpenAI servers (Studio)
- Purpose: Heavy-inference backends exposed via OpenAI-compatible APIs.
- Owner repo: external (scripts are in `/home/christopherbailey/litellm-orch/scripts`).
- Launch: scripts (`scripts/run-mlx-studio.sh`, `scripts/run-mlx-gptoss-architect.sh`, `scripts/run-mlx-test-model.sh`); launchd plist exists on Studio at `/Library/LaunchDaemons/com.bebop.mlx-launch.plist` with runtime under `/opt/mlx-launch`.
- Restart policy: not defined in scripts (launchd behavior assumed).
- Logs: `/tmp/mlx-<port>.log` per script.
- Dependencies: `/opt/mlx-launch` project and HF cache on Studio.
- Runtime status: lsof check on Studio returned no listening sockets on 8100-8109 at capture time (runtime state can vary).
- Evidence:
  ```
  --host 0.0.0.0 --port 8103 --log-file "/tmp/mlx-8103.log"
  ```
  ```
  /Library/LaunchDaemons/com.bebop.mlx-launch.plist
  /opt/mlx-launch
  ```

## Ollama
- Purpose: Existing LLM service, must not be modified.
- Owner repo: system package (not in this repo set).
- Launch: systemd unit `/etc/systemd/system/ollama.service` with override in `/etc/systemd/system/ollama.service.d/override.conf`.
- Restart policy: `Restart=always`, `RestartSec=3`
- Logs: journald (systemd).
- Evidence:
  ```
  ExecStart=/usr/local/bin/ollama serve
  Environment="OLLAMA_HOST=0.0.0.0:11434"
  ```

## Home Assistant (DietPi)
- Purpose: Home automation service (not integrated with this repo yet).
- Owner repo: external (DietPi/Home Assistant).
- Launch: systemd-managed OS package install (no Docker), running as root.
- Restart policy: managed by systemd (details not documented here).
- Logs: journald on DietPi (details not documented here).
- Dependencies: DietPi host `192.168.1.70` (verified in `/home/christopherbailey/.ssh/config`), port `8123`.
- Evidence: `/home/christopherbailey/.ssh/config`, user confirmation.

## Notes
- User systemd default target enables the OpenVINO user service.
  Evidence: `/home/christopherbailey/.config/systemd/user/default.target.wants/ov-server.service`
