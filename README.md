# homelab-llm

Monorepo for a home LLM platform built around a single LiteLLM gateway plus
specialized inference, interface, tool, and data services.

## Start Here
- Root agent contract: `AGENTS.md`
- Documentation hub: `docs/_core/README.md`
- Active work: `NOW.md`

## How to Read This Repo
- Start with root `AGENTS.md`, then follow `docs/_core/README.md`.
- Use `docs/PLATFORM_DOSSIER.md` and `docs/foundation/topology.md` for current
  runtime truth.
- Use `docs/INTEGRATIONS.md` for gateway and service-boundary wiring.
- Use `docs/OPENCODE.md` for the repo-local coding-agent control plane.
- Treat `NOW.md` as project status only, not as a concurrent-effort registry.
- See `next-projects/` for future-looking work that is not current canon.
- Treat repo root as a narrow control surface. Historical campaigns live under
  `docs/journal/` and `docs/archive/`, not at repo root.

## Service Conventions
- Service bundle convention:
  `README.md`, `SERVICE_SPEC.md`, `ARCHITECTURE.md`, `AGENTS.md`,
  `CONSTRAINTS.md`, `RUNBOOK.md`, `TASKS.md`.
- Runtime configs and secrets live outside the repo; see
  `docs/foundation/topology.md`.
- Use `uv` for Python services; avoid system Python changes.
- Naming: registry keys use `snake_case`; registry values use `kebab-case`
  where applicable.
- Showroom/backroom rule: only models present on the Mini or Studio are exposed
  as LiteLLM handles; Seagate storage is backroom-only.

## Agent Expectations
- Follow root `AGENTS.md` and `docs/_core/SOURCES_OF_TRUTH.md`.
- Follow constraints in `docs/foundation/constraints-and-decisions.md`.
- Keep LiteLLM as the single client-facing model/API gateway unless a service
  document explicitly marks a path as operator-only or internal.
- Do not change or reuse ports without an explicit migration plan.
- Do not expose new LAN-facing services without approval.
- Use `uv` for Python dependency management; avoid system Python changes.
- Keep secrets out of the repo; use env files in documented locations.
