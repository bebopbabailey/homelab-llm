# 07-SECURITY_BOUNDARIES

## LAN vs localhost exposure (derived)
- LAN-exposed (bind 0.0.0.0):
  - LiteLLM proxy on port 4000.
    Evidence: `/etc/systemd/system/litellm-orch.service`
  - Open WebUI on port 3000.
    Evidence: `/etc/systemd/system/open-webui.service`
  - OpenVINO backend on port 9000.
    Evidence: `/home/christopherbailey/.config/systemd/user/ov-server.service`
  - Ollama on port 11434.
    Evidence: `/etc/systemd/system/ollama.service.d/override.conf`
  - MLX servers on ports 8100-8103 and 8109 (Studio scripts bind 0.0.0.0).
    Evidence: `/home/christopherbailey/litellm-orch/scripts/run-mlx-studio.sh`
- LAN-exposed on DietPi:
  - Home Assistant on `192.168.1.70:8123`.
    Evidence: user confirmation
- Localhost-only (documented):
  - OpenVINO is described as localhost-only in docs; in practice it binds 0.0.0.0 for maintenance access.
    Evidence: `/home/christopherbailey/litellm-orch/docs/security.md` (doc), user confirmation

## Secret handling patterns
- LiteLLM secrets and base URLs are stored in `config/env.local` (git-ignored).
  Evidence: `/home/christopherbailey/litellm-orch/config/env.local`
- Open WebUI secret key is stored in `/home/christopherbailey/open-webui/.webui_secret_key`.
  Evidence: `/home/christopherbailey/open-webui/.webui_secret_key` (file presence)
- OpenVINO service env is stored in `/home/christopherbailey/.config/ov-llm-server/ov-server.env`.
  Evidence: `/home/christopherbailey/.config/ov-llm-server/ov-server.env`
- A secret-like token appears at the end of `docs/tinyagents-integration.md`; treat as sensitive and consider scrubbing if real.
  Evidence: `/home/christopherbailey/litellm-orch/docs/tinyagents-integration.md`

## Guardrails aligned to current patterns
- No new LAN ports without an explicit phase task and registry update.
  Evidence: `/home/christopherbailey/litellm-orch/TASKS.md`, `02-PORTS_ENDPOINTS_REGISTRY.md`
- Do not bypass LiteLLM as the gateway for new services.
  Evidence: `/home/christopherbailey/litellm-orch/DEV_CONTRACT.md`, `/home/christopherbailey/litellm-orch/ARCHITECTURE.md`
- Keep log output centralized (journald or designated log files) and avoid logging secrets.
  Evidence: `/home/christopherbailey/litellm-orch/config/router.yaml`
- Tailscale is referenced as a preferred access path; ACLs are managed in Tailscale admin (details not documented here).
  Evidence: `/home/christopherbailey/litellm-orch/docs/security.md`, user confirmation
- Tailscale IP for Mini: `100.69.99.60` (verified in `/proc/net/fib_trie`).
