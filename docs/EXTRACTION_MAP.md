# EXTRACTION_MAP

## Key artifacts scanned
- `/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch` (configs, docs, scripts)
- `/home/christopherbailey/homelab-llm/layer-inference/ov-llm-server` (OpenVINO backend)
- Systemd units and env files under `/etc/systemd/system`, `/etc/open-webui`,
  `/etc/homelab-llm`, `/etc/searxng`
- Host/network evidence: `/home/christopherbailey/.ssh/config`, `/proc/net/fib_trie`

## Conflicts found
- OpenVINO binds 0.0.0.0 for maintenance access; internal callers use localhost.
- MLX ports 8100-8109 are reserved and managed via `platform/ops/scripts/mlxctl`.

## Notes
- Open WebUI systemd unit uses `/home/christopherbailey/homelab-llm/layer-interface/open-webui`.
- A legacy install directory may exist at `/home/christopherbailey/open-webui`.
