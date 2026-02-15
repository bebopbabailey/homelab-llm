# Agent Guidance: Prometheus

## Scope
Only change `layer-tools/prometheus/*` config/docs.

## Non-negotiables
- Keep Prometheus bound to localhost (`127.0.0.1:9090`).
- Do not commit secrets (tokens, basic-auth creds).
- Prefer adding new scrape targets via config + docs updates, not ad-hoc changes.

