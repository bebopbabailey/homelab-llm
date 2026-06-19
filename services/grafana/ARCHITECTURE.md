# Grafana (Architecture)

Grafana is installed as a system package on the Mini and runs as
`grafana-server.service`. Grafana also owns the local trace-stack config for
the first OpenTelemetry cockpit slice:

- Alloy receives app OTLP traces on `127.0.0.1:4317` and `127.0.0.1:4318`.
- Tempo stores traces locally and serves Grafana on `127.0.0.1:3200`.
- Tempo retention is `48h` because local LLM prompt/response content is
  captured for debugging.

This repo provides:
- configuration (`config/`)
- provisioning (`provisioning/`)
- dashboards (`dashboards/`)

Runtime copies live under `/etc/homelab-llm/grafana/` (see `SERVICE_SPEC.md`).
