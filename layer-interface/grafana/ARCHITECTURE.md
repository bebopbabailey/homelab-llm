# Grafana (Architecture)

Grafana is installed as a system package on the Mini and runs as
`grafana-server.service`.

This repo provides:
- configuration (`config/`)
- provisioning (`provisioning/`)
- dashboards (`dashboards/`)

Runtime copies live under `/etc/homelab-llm/grafana/` (see `SERVICE_SPEC.md`).

