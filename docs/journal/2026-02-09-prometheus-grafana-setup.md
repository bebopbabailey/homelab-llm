# 2026-02-09 — Prometheus + Grafana (Mini)

## Summary
- Added Prometheus (tools layer) and Grafana (interface layer) on the Mini as localhost-only services.
- Prometheus scrapes LiteLLM `/metrics/` with bearer auth; Grafana provisions a minimal LiteLLM dashboard.

## Changes
- Prometheus installed via apt; service enabled.
- Grafana installed via Grafana apt repo; service enabled.
- Runtime configs deployed to `/etc/homelab-llm/` to avoid systemd `ProtectHome` restrictions.
- Repo configs remain source of truth; runtime copies are deployed from repo.

## Runtime paths
- Prometheus:
  - Config: `/etc/homelab-llm/prometheus/prometheus.yml`
  - Token: `/etc/homelab-llm/prometheus/litellm_bearer_token`
- Grafana:
  - Config: `/etc/homelab-llm/grafana/grafana.ini`
  - Provisioning: `/etc/homelab-llm/grafana/provisioning/`
  - Dashboards: `/etc/homelab-llm/grafana/dashboards/`

## Notes
- Prometheus scrape auth uses a bearer token file; directory permissions must allow the `prometheus` user to read it.

## Validation
- Prometheus: `curl http://127.0.0.1:9090/-/ready`
- Grafana: `curl http://127.0.0.1:3001/api/health`
- LiteLLM metrics: `curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://127.0.0.1:4000/metrics/`
