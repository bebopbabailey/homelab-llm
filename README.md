# homelab-llm

Monorepo for a home LLM platform connecting multiple small models, tools, and
utility services behind a single LiteLLM gateway.

## Start Here
- Architecture overview: `docs/foundation/README.md`
- Current topology and ports: `docs/foundation/topology.md`
- System constraints and decisions: `docs/foundation/constraints-and-decisions.md`
- Platform dossier (authoritative): `docs/PLATFORM_DOSSIER.md`
- Integration details: `docs/INTEGRATIONS.md`
- Experiment journal: `docs/journal/index.md`
- Active delivery plan: `TASKS.md`

## How to Read This Repo
- Read `docs/foundation/README.md` first; it points to the canonical sources of truth.
- Use `docs/PLATFORM_DOSSIER.md` for the latest topology and exposure details.
- Check `docs/INTEGRATIONS.md` before wiring new services into LiteLLM.
- Treat `TASKS.md` as the active plan and update it before and after changes.

## Service Conventions
- Target convention: each service should include `SERVICE_SPEC.md`, `ARCHITECTURE.md`, and `AGENTS.md`.
- Runtime configs and secrets live outside the repo; see `docs/foundation/topology.md`.
- Use `uv` for Python services; avoid system Python changes.

## Service Index
Stable services:
- LiteLLM gateway — `services/litellm-orch`
- OpenVINO LLM server — `services/ov-llm-server`
- OptiLLM proxy — `services/optillm-proxy`
- SearXNG — `services/searxng`
- Open WebUI — documented in `docs/PLATFORM_DOSSIER.md`
- MLX OpenAI servers — documented in `docs/PLATFORM_DOSSIER.md`
- Ollama — documented in `docs/PLATFORM_DOSSIER.md`
- Home Assistant — documented in `docs/PLATFORM_DOSSIER.md`

Planned services (endpoints):
- TinyAgents (planned client/orchestrator behind LiteLLM)
- OptiLLM (planned expansion of optimization endpoints)

## Ops Scripts (core)
- `ops/scripts/healthcheck.sh`
- `ops/scripts/restart-all.sh`
- `ops/scripts/redeploy.sh`

## Documentation Hygiene
- Keep service docs, topology, and integrations in sync with changes.
- Update `TASKS.md` before and after implementing new features.


## Agent Expectations
See `docs/foundation/README.md` for the canonical agent expectations.
- Follow constraints in `docs/foundation/constraints-and-decisions.md`.
- Keep LiteLLM as the single gateway; do not bypass it.
- Do not change or reuse ports without an explicit migration plan.
- Do not expose new LAN-facing services without approval.
- Use `uv` for Python dependency management; avoid system Python changes.
- Keep secrets out of the repo; use env files in documented locations.
