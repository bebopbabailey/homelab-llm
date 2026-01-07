# 05-INTEGRATIONS_OPENWEBUI

## Open WebUI -> LiteLLM wiring
- Open WebUI uses OpenAI-compatible settings and points to LiteLLM via loopback.
  Evidence: `/etc/open-webui/env`
  ```
  OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1
  OPENAI_API_KEY=dummy
  ENABLE_OPENAI_API=true
  ```
 - Health check is available at `/health` on port 3000.
   Evidence: `curl http://127.0.0.1:3000/health`

## Config locations
- System service env file: `/etc/open-webui/env`
- Systemd unit (system): `/etc/systemd/system/open-webui.service`
- Data dir: `/home/christopherbailey/.open-webui` (from env)
 - Active unit: system `open-webui.service` is enabled/active; user unit removed.
   Evidence: `systemctl is-enabled open-webui.service`, `systemctl is-active open-webui.service`

Evidence (systemd unit):
```
ExecStart=/home/christopherbailey/open-webui/.venv/bin/open-webui serve --host 0.0.0.0 --port 3000
EnvironmentFile=/etc/open-webui/env
```

## Auth headers and base URL
- Open WebUI sends OpenAI-compatible requests using `OPENAI_API_KEY` (currently `dummy`) and `OPENAI_API_BASE_URL`.
  Evidence: `/etc/open-webui/env`, `/home/christopherbailey/.config/open-webui/env`

## Notes
- Open WebUI docs in this repo state it listens on `http://<mini-host>:3000` by default.
  Evidence: `/home/christopherbailey/litellm-orch/docs/openwebui.md`
- The systemd unit binds 0.0.0.0:3000, which is LAN-exposed unless restricted by firewall.
  Evidence: `/etc/systemd/system/open-webui.service`
- User confirmed `/health` is exposed on port 3000.
