# homelab-llm

Monorepo for a home LLM platform connecting multiple small models, tools, and
utility services behind a single LiteLLM gateway. The goal is to create a very capable personal 
AI assistant platform for personal use, but to learn implementation of agent pipelines, tool use, etc. 
The variety of hardware in the lab allows testing various use cases, minimum hardware requirements by 
use-case. Hopes of branching into enterprise-land later.

## Start Here
- Architecture overview: `docs/foundation/README.md`
- Current topology and ports: `docs/foundation/topology.md`
- System constraints and decisions: `docs/foundation/constraints-and-decisions.md`
- Platform dossier (authoritative): `docs/PLATFORM_DOSSIER.md`
- Integration details: `docs/INTEGRATIONS.md`
- Experiment journal: `docs/journal/index.md`
- Active delivery plan: `TASKS.md`
- Submodule workflow: `docs/foundation/git-submodules.md`
- System architecture: `docs/ARCHITECTURE.md`

## How to Read This Repo
- Read `docs/foundation/README.md` first; it points to the canonical sources of truth.
- Use `docs/PLATFORM_DOSSIER.md` for the latest topology and exposure details.
- Check `docs/INTEGRATIONS.md` before wiring new services into LiteLLM.
- Treat `TASKS.md` as the active plan and update it before and after changes.
- See `/next-projects`for documentation of software development plans, upcoming features.

## Service Conventions
- Target convention: each service should include `SERVICE_SPEC.md`, `ARCHITECTURE.md`, and `AGENTS.md`.
- Runtime configs and secrets live outside the repo; see `docs/foundation/topology.md`.
- Use `uv` for Python services; avoid system Python changes.
- Naming: registry keys use `snake_case`; registry values use `kebab-case` where applicable.
- Showroom/backroom rule: only models present on the Mini or Studio are exposed as
  LiteLLM handles; Seagate storage is backroom-only.
- OptiLLM router classifier is internal to the OptiLLM service (not a LiteLLM handle); see
  `layer-gateway/optillm-proxy/README.md`.
- Studio OptiLLM local uses HF cache at `/Users/thestudio/models/hf/hub` and pins
  `transformers<5` for router compatibility.

## Service Index
Stable services:
- LiteLLM gateway — `layer-gateway/litellm-orch`
- OpenVINO LLM server — `layer-inference/ov-llm-server`
- OptiLLM proxy — `layer-gateway/optillm-proxy`
- OptiLLM local (Studio) — `layer-gateway/optillm-local`
- TinyAgents — `layer-gateway/tiny-agents`
- SearXNG — `layer-tools/searxng`
- Open WebUI — documented in `docs/PLATFORM_DOSSIER.md`
- MLX OpenAI servers — documented in `docs/PLATFORM_DOSSIER.md`
- Ollama — documented in `docs/PLATFORM_DOSSIER.md`
- Home Assistant — documented in `docs/PLATFORM_DOSSIER.md`

Planned services (endpoints):
- System monitor (planned, gateway layer)
- AFM (planned OpenAI-compatible API on the Studio, routed via LiteLLM)

## Ops Scripts (core)
- `platform/ops/scripts/healthcheck.sh`
- `platform/ops/scripts/restart-all.sh`
- `platform/ops/scripts/redeploy.sh`

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
