# 2026-04-27 orchestration-cockpit phase 6 durable service

## Objective
Make `orchestration-cockpit` a real Mini-owned localhost-only experimental
service with normal `systemd` ownership while preserving the existing LangGraph
+ Agent Chat UI behavior.

## Runtime shape
- LangGraph Agent Server:
  - `127.0.0.1:2024`
- Agent Chat UI:
  - `127.0.0.1:3030`
- Specialized runtime forward remains external:
  - Mini `127.0.0.1:8129 -> Studio 127.0.0.1:8120`

## Decisions
- Keep the tracked `services/orchestration-cockpit/langgraph.json` as the
  source of truth.
- Remove repo-local `.env` authority from `langgraph.json`.
- Generate the live runtime `langgraph.json` under
  `~/.local/state/orchestration-cockpit/langgraph-runtime/` because LangGraph
  resolves graph paths relative to the runtime working directory.
- Prefer the repo/`uv` launch path under `systemd`, but redirect the
  `UV_PROJECT_ENVIRONMENT` outside the repo.
- Move default runtime artifacts to:
  - `/home/christopherbailey/.local/state/orchestration-cockpit`
- Keep Agent Chat UI stock and external under:
  - `/home/christopherbailey/.local/share/orchestration-cockpit/agent-chat-ui`
- Commit `services/orchestration-cockpit/uv.lock` as a normal service lockfile.

## Validation target
Phase 6 is complete when:
- `orchestration-cockpit-graph.service` and `orchestration-cockpit-ui.service`
  start under `systemd` without PTY help
- repo runtime dirt stays out of the tracked worktree
- localhost readiness checks pass on `2024` and `3030`
- specialized-path validation still works with the external `8129` forward

## Result
Passed.

- `orchestration-cockpit-graph.service`
  - active under `systemd`
  - disabled on boot
  - serves `http://127.0.0.1:2024/docs`
- `orchestration-cockpit-ui.service`
  - active under `systemd`
  - disabled on boot
  - serves `http://127.0.0.1:3030`
- external specialized dependency remains unchanged:
  - Mini `127.0.0.1:8129 -> Studio 127.0.0.1:8120`
- graph API checks passed for:
  - ordinary `hello`
  - specialized `/specialized S02 ...`
  - invalid `/specialized TOOL ...`
- local artifacts now live under:
  - `/home/christopherbailey/.local/state/orchestration-cockpit/`

## Implementation findings
- LangGraph did not reliably resolve relative graph paths from the tracked
  `langgraph.json` when the working directory moved outside the repo.
  Resolution:
  - keep the tracked `services/orchestration-cockpit/langgraph.json` as the
    source of truth
  - generate
    `~/.local/state/orchestration-cockpit/langgraph-runtime/langgraph.json`
    with absolute paths at launch time
- The stock Agent Chat UI was not durable under `systemd` when launched through
  `corepack` or a Volta `pnpm` shim alone.
  Resolution:
  - prefer the scaffold-local `apps/web/node_modules/.bin/next` binary
  - retain `corepack`/`pnpm` only as fallbacks
- After removing repo-local `.venv`, `.langgraph_api`, `__pycache__`, and
  `*.egg-info`, those artifacts did not return while the services stayed active.

## Operator surfaces
- `systemctl status orchestration-cockpit-graph.service --no-pager`
- `systemctl status orchestration-cockpit-ui.service --no-pager`
- `journalctl -u orchestration-cockpit-graph.service -f`
- `journalctl -u orchestration-cockpit-ui.service -f`
- `curl -fsS http://127.0.0.1:2024/docs`
- `curl -I -s http://127.0.0.1:3030`

## Local artifact proof
- run ledger:
  - `/home/christopherbailey/.local/state/orchestration-cockpit/run-ledger.jsonl`
- correlated adapter telemetry:
  - `/home/christopherbailey/.local/state/orchestration-cockpit/omlx-runtime-telemetry.jsonl`

## Closeout caveat
The installed `/etc/orchestration-cockpit/{graph,ui}.env` files currently point
`ORCHESTRATION_COCKPIT_REPO_ROOT` at the phase-6 linked worktree for
validation:
- `/home/christopherbailey/homelab-llm-orchestration-cockpit-phase6-20260427`

Before or immediately after closeout to `master`, repoint that env value to the
primary repo path and restart both services.

## Rollback
- stop both services
- remove installed unit files from `/etc/systemd/system/`
- `systemctl daemon-reload`
- verify `127.0.0.1:2024` and `127.0.0.1:3030` are clear
- keep `~/.local/share/orchestration-cockpit/` and
  `~/.local/state/orchestration-cockpit/` unless explicit cleanup is requested
