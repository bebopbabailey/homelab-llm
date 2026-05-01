# Service Spec: grafana

## Purpose
UI for LiteLLM + Prometheus observability dashboards.

## Host & Runtime
- **Host**: Mac mini (Ubuntu 24.04)
- **Bind**: `127.0.0.1:3001`
- **Tailnet operator URL**: `https://grafana.tailfd1400.ts.net/` via `svc:grafana`
- **Binary**: `grafana-server` (system package)

## Configuration
- Repo config (source of truth): `services/grafana/config/grafana.ini`
- Repo provisioning: `services/grafana/provisioning/`
- Repo dashboards: `services/grafana/dashboards/`
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
tailscale serve status --json
```
