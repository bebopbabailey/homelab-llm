# 01-PLATFORM_TOPOLOGY

## Derived topology (evidence-based)
### Mac Mini (Ubuntu 24.04, per repo docs)
- LiteLLM proxy on port 4000, systemd, bind 0.0.0.0.
  Evidence: `/etc/systemd/system/litellm-orch.service`
- Open WebUI on port 3000, systemd, bind 0.0.0.0.
  Evidence: `/etc/systemd/system/open-webui.service`
- OpenVINO LLM server on port 9000, user systemd, bind 0.0.0.0.
  Evidence: `/home/christopherbailey/.config/systemd/user/ov-server.service`
- Ollama on port 11434, systemd, bind 0.0.0.0.
  Evidence: `/etc/systemd/system/ollama.service` + `/etc/systemd/system/ollama.service.d/override.conf`

### Mac Studio (MLX backends)
- MLX OpenAI servers on ports 8100, 8101, 8102, 8103, 8109.
  Evidence: `/home/christopherbailey/litellm-orch/config/env.local` and `/home/christopherbailey/litellm-orch/scripts/run-mlx-studio.sh`
- Base URLs configured in LiteLLM env: `http://192.168.1.72:<port>/v1`.
  Evidence: `/home/christopherbailey/litellm-orch/config/env.local`
- Launch method appears to be scripts or launchd; Studio has `/Library/LaunchDaemons/com.bebop.mlx-launch.plist` and `/opt/mlx-launch`.
  Evidence: `ssh thestudio@192.168.1.72`

### HP DietPi (Home Assistant)
- Home Assistant instance at `192.168.1.70:8123` (host verified via `/home/christopherbailey/.ssh/config`; port confirmed by owner).

## Flow diagram A: Open WebUI -> LiteLLM -> upstream LLM backends
```
[Open WebUI :3000] --OPENAI_API_BASE_URL--> [LiteLLM proxy :4000]
                                           |-> [OpenVINO :9000]
                                           |-> [MLX OpenAI servers :8100/:8101/:8102/:8103/:8109]
```
Evidence: `/etc/open-webui/env`, `/etc/systemd/system/litellm-orch.service`, `/home/christopherbailey/litellm-orch/config/env.local`

## Flow diagram B: (Future) Tiny Agents -> LiteLLM -> upstream backends
```
[Tiny Agents service] --> [LiteLLM proxy :4000]
                          |-> [OpenVINO :9000]
                          |-> [MLX OpenAI servers :8100/:8101/:8102/:8103/:8109]
```
Evidence: `/home/christopherbailey/litellm-orch/docs/tinyagents-integration.md`

## Notes
- Open WebUI uses `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1` (local loopback).
  Evidence: `/etc/open-webui/env`
- Mini LAN IP: `192.168.1.71` (verified in `/proc/net/fib_trie`).
- Mini SSH alias: `ssh mini` (user confirmed).
- Studio SSH alias: `ssh studio` (verified in `/home/christopherbailey/.ssh/config`).
- Home Assistant SSH alias: `ssh hp` (verified in `/home/christopherbailey/.ssh/config`).
 - SSH aliases do not imply HTTP name resolution unless DNS/hosts are configured (note for client base URLs).
