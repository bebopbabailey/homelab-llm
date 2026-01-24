# Repository Guidelines

## Project Structure & Module Organization
- Root docs: `README.md`, `ARCHITECTURE.md`, `SERVICE_SPEC.md`, `DEV_CONTRACT.md`, `TASKS.md`, `AIDER.md`, `AGENT_PREFERENCES.md`.
- Runtime config: `config/router.yaml` and `config/env.example` (copy to `config/env.local` for real values).
- External services: OpenVINO on `localhost:9000`; MLX OpenAI servers on the Studio at ports `8100-8119` (team) and `8120-8139` (experimental).
- Source code: currently minimal (`main.py` placeholder); gateway logic will live in this repo.
- Scripts/tests: `scripts/`, `docs/`, `logs/`, and `callbacks/` are available; add runbooks and tests as phases progress.

## Build, Test, and Development Commands
There is no build or test pipeline yet. Use `uv` for all dependency management.
- `uv sync` installs pinned dependencies into `.venv`.
- `uv run python main.py` is a simple sanity check that the environment runs.
When the LiteLLM proxy entrypoint is added, document the exact command here.

## Coding Style & Naming Conventions
- Python only (3.12). Keep code minimal and configuration-driven.
- Use `snake_case` for Python modules/functions and descriptive, explicit names for config keys.
- Routing model names use handles (`mlx-*`) while upstream
  `litellm_params.model` values use `openai/<base-model>` for OpenAI-compatible backends.
- Prefer small, reversible changes; avoid hardcoding IPs/ports in Python—use env vars + `config/router.yaml`.

## Testing Guidelines
- No tests yet; add `tests/` when behavior is implemented.
- When tests exist, follow `test_*.py` naming and keep fixtures lightweight.
- Document any required local services (MLX/OpenVINO) alongside tests that depend on them.

## Commit & Pull Request Guidelines
- No commit history exists yet, so there are no established conventions.
- Suggested format: short, imperative subject lines (e.g., “Add Aider runbook”).
- PRs should include: scope summary, config changes, and any required environment variables.

## Task Alignment & Agent Behavior
- `TASKS.md` is the source of truth for phases and scope. **MUST** update it before adding new features.
- **MUST** follow `AGENT_PREFERENCES.md`: prefer small, reversible changes and keep docs current.
- **MUST** honor `DEV_CONTRACT.md` constraints: routing-only, no inference, use `uv`, and **DO NOT** modify existing services.
- **MUST** treat the MLX registry as the source of truth; use `mlxctl sync-gateway` to update router/env/handles.

## Security & Configuration Tips
- **DO NOT** touch existing services (OLLAMA on `11434`, OpenVINO on `9000`).
- MLX OpenAI servers run on the Studio at ports `8100-8119` (team) and `8120-8139` (experimental).
- Keep secrets and hostnames in `config/env.local` (git-ignored).
- The gateway is routing-only; inference must remain external.
