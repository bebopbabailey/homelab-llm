# Service Spec: prometheus

## Purpose
Metrics backend for LiteLLM and related services.

## Host & Runtime
- **Host**: Mac mini (Ubuntu 24.04)
- **Bind**: `127.0.0.1:9090` (tailnet HTTPS via Tailscale Serve if needed)
- **Binary**: `prometheus` (system package)

## Configuration
- Repo config (source of truth): `layer-tools/prometheus/config/prometheus.yml`
- Runtime config (deployed copy): `/etc/homelab-llm/prometheus/prometheus.yml`
- Metrics auth token file (not in git): `/etc/homelab-llm/prometheus/litellm_bearer_token`

## Scrape Targets
- LiteLLM proxy on `127.0.0.1:4000` (`/metrics/`, auth required)

## Health
- `/-/ready`
- `/-/healthy`

## Validation
```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9090/-/healthy
```

## Notes
- Do not store secrets in the repo. Use the credentials file path above.
