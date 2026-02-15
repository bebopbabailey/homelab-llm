# Agent Guidance: Grafana

## Scope
Only change `layer-interface/grafana/*` (dashboards, provisioning, config docs).

## Non-negotiables
- Do not change Grafana bind/port without an explicit plan (canonical port is `127.0.0.1:3001`).
- Do not commit secrets (admin passwords, API keys, tokens).
- Prefer editing dashboards/provisioning in this repo and deploying copies via ops.

