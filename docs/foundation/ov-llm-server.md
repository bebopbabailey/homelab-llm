# OV LLM Server (OpenVINO)

## Purpose
Local OpenVINO-based LLM endpoint for fast/low-cost inference on the Mini.

## Source of truth
- Host/ports: `docs/foundation/topology.md`
- Contracts: `docs/_core/SOURCES_OF_TRUTH.md`

## Service identity
- Host: Mini
- Port: 9000
- Base URL: http://127.0.0.1:9000
- Health: /health

## Launch + config
- Env file: `/etc/homelab-llm/ov-server.env`
- Ownership: Mini-only service

## Safe validation
- `curl -fsS http://127.0.0.1:9000/health`
- `curl -fsS http://127.0.0.1:9000/v1/models`

## Notes
- Keep config changes documented in `docs/foundation/ov-llm-server.md`.
- Do not change ports without updating `docs/foundation/topology.md`.
