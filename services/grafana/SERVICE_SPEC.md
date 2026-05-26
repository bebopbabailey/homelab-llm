# Service Spec: grafana

## Purpose
UI for LiteLLM + Prometheus observability dashboards, and owner of the
Mini-local OpenTelemetry trace stack.

## Host & Runtime
- **Host**: Mac mini (Ubuntu 24.04)
- **Bind**: `127.0.0.1:3001`
- **Tailnet operator URL**: `https://grafana.tailfd1400.ts.net/` via `svc:grafana`
- **Binary**: `grafana-server` (system package)
- **Trace collector**: `alloy` (system package), OTLP on `127.0.0.1:4317/4318`
- **Trace backend**: `tempo` (system package), query API on `127.0.0.1:3200`

## Configuration
- Repo config (source of truth): `services/grafana/config/grafana.ini`
- Repo Alloy config: `services/grafana/config/alloy.river`
- Repo Tempo config: `services/grafana/config/tempo.yaml`
- Repo provisioning: `services/grafana/provisioning/`
- Repo dashboards: `services/grafana/dashboards/`
- Runtime config (deployed copy): `/etc/homelab-llm/grafana/grafana.ini`
- Runtime Alloy config: `/etc/homelab-llm/grafana/alloy.river`
- Runtime Tempo config: `/etc/homelab-llm/grafana/tempo.yaml`
- Runtime provisioning: `/etc/homelab-llm/grafana/provisioning/`
- Runtime dashboards: `/etc/homelab-llm/grafana/dashboards/`

## Default Dashboards
- LiteLLM Overview (RPS, error rate, p95 latency, p95 TTFT, TPS)

## Health
- `GET /api/health`
- Tempo: `GET http://127.0.0.1:3200/ready`
- Alloy: `GET http://127.0.0.1:12345/-/ready` when the package UI listener is
  enabled by its runtime defaults

## Validation
```bash
curl -fsS http://127.0.0.1:3001/api/health
curl -fsS http://127.0.0.1:3200/ready
tailscale serve status --json
```
