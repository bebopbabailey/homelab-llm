# EXTRACTION_MAP

## Key artifacts scanned
- `/home/christopherbailey/litellm-orch` (configs, docs, scripts)
- `/home/christopherbailey/ov-llm-server` (OpenVINO backend)
- Systemd units and env files under `/etc/systemd/system`, `/etc/open-webui`, `/home/christopherbailey/.config`
- Host/network evidence: `/home/christopherbailey/.ssh/config`, `/proc/net/fib_trie`

## Conflicts found
- OpenVINO docs say localhost-only; unit binds 0.0.0.0.
- OpenVINO env fp16 in repo vs fp32 in active env.
- MLX port list mismatch in docs vs env; env is source of truth.

## Missing expected artifacts (UNVERIFIED)
- `/home/christopherbailey/OpenVINO` repo not found (active backend is `/home/christopherbailey/ov-llm-server`).
- Open WebUI repo content not present (only install dir at `/home/christopherbailey/open-webui`).
