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
- `OPENAI_API_KEY="<key>" OPTILLM_API_KEY="<key>" uv run optillm --host 127.0.0.1 --port 4020 --base-url http://127.0.0.1:4000/v1 --approach none --model <base-model>`

## Coding Style & Naming Conventions
- This service is a thin proxy; keep changes configuration-driven.
- Use plain logical model names for LiteLLM aliases (e.g., `plan-architect`).
- OptiLLM approach selection is passed in request body as `optillm_approach`.

## Testing Guidelines
- Minimal validation is via HTTP health and `/v1/models`.
- Keep tests light; prefer curl-based smoke checks unless code is added.

## Operational Constraints
- Bind to `127.0.0.1` only; never expose on LAN.
- OptiLLM may call LiteLLM or MLX upstream depending on the active routing policy.
- Ports are immutable; this service uses port `4020`.
- MCP or other plugins should be planned and documented before enabling.
- Do not store secrets in the repo.

## Integration Requirements
When adding this service to the system:
- Keep LiteLLM routing **direct** to MLX by default.
- OptiLLM is called explicitly at `http://127.0.0.1:4020/v1` when needed.
- Update `platform/ops/scripts/healthcheck.sh` and `platform/ops/scripts/restart-all.sh`.
- Add a systemd unit in `platform/ops/systemd/` and an env file outside the repo.

## Systemd Expectations (planned)
- Prefer a system-level unit: `/etc/systemd/system/optillm-proxy.service`.
- Use `EnvironmentFile=/etc/optillm-proxy/env` for secrets.
- ExecStart should pass explicit flags for host, port, base URL, approach, model.

## Current Task: OptiLLM ensembles (2026-01)
Goal: implement multi-model OptiLLM ensembles (no single-model configs) across
`xl`, `l`, `m`, `s` tiers plus `high`, `balanced`, `fast`.

### Required changes (in order)
1) **Update LiteLLM routing**
   - File: `layer-gateway/litellm-orch/config/router.yaml`
   - Ensure `litellm_settings.drop_params: false` for param pass-through.
   - Keep MLX handles routed directly to MLX ports.

2) **Optional: handles registry**
   - File: `layer-gateway/registry/handles.jsonl`
   - Only add `opt-*` handles if we explicitly want separate OptiLLM entrypoints.
   - Default is **no opt-* handles**; keep base handles and use `optillm_approach`.

3) **Update OptiLLM proxy config**
   - File: `~/.optillm/proxy_config.yaml`
   - Ensure upstream points to LiteLLM only (`http://127.0.0.1:4000/v1`).
   - Verify enabled plugins and approach expectations.

4) **Docs**
   - Update `docs/foundation/optillm-techniques.md` with tier guidance.
   - Update `docs/INTEGRATIONS.md` if new handles are exposed.
   - Update `docs/journal/*` with decision and rationale.

### Validation checklist
- `python3 scripts/validate_handles.py`
- `curl -fsS http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | rg '^mlx-'`
- Optional OptiLLM smoke test (direct):
  - `curl -fsS http://127.0.0.1:4020/v1/chat/completions -H "Authorization: Bearer $OPTILLM_API_KEY" -H "Content-Type: application/json" -d '{"model":"mlx-<handle>","messages":[{"role":"user","content":"ping"}],"optillm_approach":"bon","max_tokens":16}'`

### Ensemble helpers
- OV utility ensembles (Mini):
  - `ovctl ensemble opt-route-fast-s`
  - `ovctl ensemble opt-extract-fast-s`
  - `ovctl ensemble opt-clean-fast-s`
  - `ovctl ensemble opt-summarize-fast-s`
  - `ovctl ensemble opt-privacy-fast-s`
- MLX ensembles (Studio):
  - `mlxctl ensemble opt-architect-high-xl`
  - `mlxctl ensemble opt-research-high-xl`
  - `mlxctl ensemble opt-architect-balanced-l`
  - `mlxctl ensemble opt-code-balanced-l`
  - `mlxctl ensemble opt-chat-balanced-m`

### Constraints
- Registry values use kebab-case only (letters, digits, dashes).
- OptiLLM approaches must match the OptiLLM approach registry (dash/underscore as provided).
- Do not edit files under `docs/archive/`.
- Do not create single-model OptiLLM configs for this phase.
