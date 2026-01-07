# INTEGRATIONS

## LiteLLM routing
- Config: `config/router.yaml` + `config/env.local`.
- Router settings: retries and cooldowns in `config/router.yaml`.
- Upstreams: MLX `http://192.168.1.72:<port>/v1`, OpenVINO `http://localhost:9000/v1`.
- Model naming: plain `jerry-*`, `lil-jerry`; upstream model IDs use `openai/<upstream>`.
- Logs: JSON logs enabled (`litellm_settings.json_logs: true`).
- Auth: proxy key planned via `LITELLM_PROXY_KEY`.

## Open WebUI -> LiteLLM
- Env: `/etc/open-webui/env` uses `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`.
- Health: `/health` on port 3000.

## OpenVINO backend
- User systemd unit: `/home/christopherbailey/.config/systemd/user/ov-server.service`.
- Endpoints: `/health`, `/v1/models`, `/v1/chat/completions`.
- LiteLLM routes `lil-jerry` via `LIL_JERRY_API_BASE` and `LIL_JERRY_MODEL`.

## Tiny Agents hook (plan)
- Add `TINYAGENTS_API_BASE` and `TINYAGENTS_MODEL` to env.
- Add a `model_list` entry in `config/router.yaml`.
- Update `PLATFORM_DOSSIER.md` before new LAN exposure.

## Client base URL recommendation
- Prefer `http://mini:4000` only if name resolution is configured.
- Fallback: `http://192.168.1.71:4000`.
