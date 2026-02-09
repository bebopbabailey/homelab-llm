# Service Spec: grafana

## Purpose
UI for LiteLLM + Prometheus observability dashboards.

## Host & Runtime
- **Host**: Mac mini (Ubuntu 24.04)
- **Bind**: `127.0.0.1:3001` (tailnet HTTPS via Tailscale Serve if needed)
- **Binary**: `grafana-server` (system package)

## Configuration
- Repo config (source of truth): `layer-interface/grafana/config/grafana.ini`
- Repo provisioning: `layer-interface/grafana/provisioning/`
- Repo dashboards: `layer-interface/grafana/dashboards/`
- Runtime config (deployed copy): `/etc/homelab-llm/grafana/grafana.ini`
- Runtime provisioning: `/etc/homelab-llm/grafana/provisioning/`
- Runtime dashboards: `/etc/homelab-llm/grafana/dashboards/`

## Default Dashboards
- LiteLLM Overview (RPS, error rate, p95 latency, p95 TTFT, TPS)

## Health
- `GET /api/health`

## Validation
```bash
curl -fsS http://127.0.0.1:3001/api/health
```
