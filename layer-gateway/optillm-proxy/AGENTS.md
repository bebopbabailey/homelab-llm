# Repository Guidelines

## Project Structure & Module Organization
- Service docs live in `README.md` and `SERVICE_SPEC.md`.
- This service is a localhost-only proxy that sits behind LiteLLM.
- Reference platform constraints in `docs/foundation/constraints-and-decisions.md`.
- Reference topology in `docs/foundation/topology.md`.

## Build, Test, and Development Commands
Use `uv` only. Do not use Docker.
- `uv venv .venv`
- `uv pip install optillm==0.3.12`
- `OPENAI_API_KEY="<key>" OPTILLM_API_KEY="<key>" uv run optillm --host 127.0.0.1 --port 4020 --base-url http://127.0.0.1:4000/v1 --approach auto --model jerry-chat`

## Coding Style & Naming Conventions
- This service is a thin proxy; keep changes configuration-driven.
- Use plain logical model names for LiteLLM aliases (e.g., `plan-architect`).
- OptiLLM uses prefixed model names for approaches (`moa-jerry-chat`).

## Testing Guidelines
- Minimal validation is via HTTP health and `/v1/models`.
- Keep tests light; prefer curl-based smoke checks unless code is added.

## Operational Constraints
- Bind to `127.0.0.1` only; never expose on LAN.
- Do not bypass LiteLLM. OptiLLM must call LiteLLM upstream only.
- Ports are immutable; this service uses port `4020`.
- MCP or other plugins should be planned and documented before enabling.
- Do not store secrets in the repo.

## Integration Requirements
When adding this service to the system:
- Add a LiteLLM route that points to `http://127.0.0.1:4020/v1`.
- Ensure LiteLLM sends prefixed model names to OptiLLM (avoid loops).
- Update `platform/ops/scripts/healthcheck.sh` and `platform/ops/scripts/restart-all.sh`.
- Add a systemd unit in `platform/ops/systemd/` and an env file outside the repo.

## Systemd Expectations (planned)
- Prefer a system-level unit: `/etc/systemd/system/optillm-proxy.service`.
- Use `EnvironmentFile=/etc/optillm-proxy/env` for secrets.
- ExecStart should pass explicit flags for host, port, base URL, approach, model.
