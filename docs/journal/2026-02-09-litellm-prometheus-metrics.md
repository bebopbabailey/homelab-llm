# 2026-02-09 — LiteLLM Prometheus Metrics

## Goal
Enable Prometheus metrics on the LiteLLM proxy and document Grafana queries.

## Changes
- Enabled Prometheus callback in `router.yaml`.
- Installed `prometheus_client` in the LiteLLM venv.
- `/metrics/` now serves Prometheus metrics on the LiteLLM port.

## Notes
- Metrics are on the same port as the proxy (`/metrics/`).
- Use `/metrics/` to confirm actual metric names before building dashboards.
