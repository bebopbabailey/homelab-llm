# Runbook: orchestration-cockpit

## Purpose
Own the localhost-only Mini cockpit service in its current local/dev runtime
shape without changing the commodity chat surface.

## Preconditions
- Keep all binds on localhost only.
- Do not run on port `3000`; Open WebUI already owns that port.
- Establish the specialized-runtime path externally before testing the
  specialized branch:
  - Studio oMLX listener on `127.0.0.1:8120`
  - Mini SSH forward on `127.0.0.1:8129`

## Runtime ownership
Phase 6 defines the supported host-owned paths:
- Agent Chat UI root:
  - `/home/christopherbailey/.local/share/orchestration-cockpit/agent-chat-ui`
- runtime state/artifacts:
  - `/home/christopherbailey/.local/state/orchestration-cockpit`
- installed env files:
  - `/etc/orchestration-cockpit/graph.env`
  - optional `/etc/orchestration-cockpit/graph.secret.env`
  - `/etc/orchestration-cockpit/ui.env`

Repo-local `.env` remains manual-only convenience for non-systemd runs. It is
not the durable service authority.

## Env templates
Copy the repo-managed templates into `/etc/orchestration-cockpit/` and edit
them locally:
```bash
sudo install -d -m 0755 /etc/orchestration-cockpit
sudo install -m 0644 platform/ops/templates/orchestration-cockpit.graph.env.example /etc/orchestration-cockpit/graph.env
sudo install -m 0644 platform/ops/templates/orchestration-cockpit.graph.secret.env.example /etc/orchestration-cockpit/graph.secret.env
sudo install -m 0644 platform/ops/templates/orchestration-cockpit.ui.env.example /etc/orchestration-cockpit/ui.env
```

Required graph env values:
- `ORCHESTRATION_COCKPIT_REPO_ROOT=/home/christopherbailey/homelab-llm`
- `OMLX_RUNTIME_BASE_URL=http://127.0.0.1:8129`
- `OMLX_RUNTIME_BEARER_TOKEN=...`
- `OMLX_RUNTIME_MODEL=Qwen3-4B-Instruct-2507-4bit`
- `ORCHESTRATION_COCKPIT_STATE_DIR=/home/christopherbailey/.local/state/orchestration-cockpit`
- optional `UV_PROJECT_ENVIRONMENT=/home/christopherbailey/.local/share/orchestration-cockpit/graph-venv`

Optional graph secret env:
- `LANGSMITH_API_KEY=...` only if `langgraph dev` still requires it locally

Required UI env values:
- `ORCHESTRATION_COCKPIT_UI_ROOT=/home/christopherbailey/.local/share/orchestration-cockpit/agent-chat-ui`
- `NEXT_PUBLIC_API_URL=http://127.0.0.1:2024`
- `NEXT_PUBLIC_ASSISTANT_ID=operator-cockpit`
- `ORCHESTRATION_COCKPIT_UI_PORT=3030`
- `ORCHESTRATION_COCKPIT_NEXT_BIN=/home/christopherbailey/.local/share/orchestration-cockpit/agent-chat-ui/apps/web/node_modules/.bin/next`
- `ORCHESTRATION_COCKPIT_COREPACK_BIN=/home/christopherbailey/.volta/tools/image/node/24.13.0/bin/corepack`

## Python setup
```bash
uv sync --project services/orchestration-cockpit
uv run --project services/orchestration-cockpit python -m unittest discover -s services/orchestration-cockpit/tests -p 'test_*.py'
```

## Generated service artifacts
Render the canonical graph diagram from code:
```bash
uv run --project services/orchestration-cockpit python services/orchestration-cockpit/scripts/render_graph_diagram.py
```

Verify the local service contract surfaces:
```bash
uv run --project services/orchestration-cockpit python services/orchestration-cockpit/scripts/verify_local_runtime.py
```

## LangGraph dev server
If local tooling requires a LangSmith key, export it locally first. It is a
dev-server prerequisite only; it is not part of cockpit auth.

```bash
uv tool install "langgraph-cli[inmem]"
/home/christopherbailey/homelab-llm/services/orchestration-cockpit/scripts/run_langgraph_dev.sh
```

Important:
- the tracked `langgraph.json` remains the source of truth, but the wrapper
  generates a runtime config copy with absolute paths under
  `~/.local/state/orchestration-cockpit/langgraph-runtime/langgraph.json`
- the wrapper redirects the `uv` project environment and LangGraph runtime
  working directory outside the repo
- the graph must not compile with a custom checkpointer; `langgraph dev`
  rejects that shape and manages persistence itself

## Agent Chat UI (not vendored)
Option 1: local scaffold in the supported durable root
```bash
mkdir -p /home/christopherbailey/.local/share/orchestration-cockpit
cd /home/christopherbailey/.local/share/orchestration-cockpit
npx create-agent-chat-app --project-name agent-chat-ui
cd agent-chat-ui
cp /home/christopherbailey/homelab-llm/services/orchestration-cockpit/ui/.env.example apps/web/.env.local
corepack pnpm install
export ORCHESTRATION_COCKPIT_UI_ROOT="$PWD"
/home/christopherbailey/homelab-llm/services/orchestration-cockpit/scripts/run_agent_chat_ui.sh
```

Option 2: separate local checkout of `langchain-ai/agent-chat-ui`

Required UI env:
- `NEXT_PUBLIC_API_URL=http://127.0.0.1:2024`
- `NEXT_PUBLIC_ASSISTANT_ID=operator-cockpit`

Important:
- do not use the scaffold's root `pnpm dev` command in this phase
- that bundled dev script also tries to start its own agent server on `:2024`
  and defaults the web app to the commodity `:3000` collision path
- for this repo, point the web app at the existing local LangGraph server on
  `127.0.0.1:2024` and bind the UI itself to `127.0.0.1:3030`

## systemd install/start/stop
Install the repo-managed units:
```bash
sudo install -m 0644 platform/ops/systemd/orchestration-cockpit-graph.service /etc/systemd/system/orchestration-cockpit-graph.service
sudo install -m 0644 platform/ops/systemd/orchestration-cockpit-ui.service /etc/systemd/system/orchestration-cockpit-ui.service
sudo systemctl daemon-reload
```

Start and verify them:
```bash
sudo systemctl start orchestration-cockpit-graph.service
sudo systemctl start orchestration-cockpit-ui.service
systemctl status orchestration-cockpit-graph.service --no-pager
systemctl status orchestration-cockpit-ui.service --no-pager
curl -fsS http://127.0.0.1:2024/docs >/dev/null && echo "langgraph ok"
curl -fsS http://127.0.0.1:3030 >/dev/null && echo "ui ok"
```

Do not enable them on boot in phase 6.

## Manual browser checks
1. ordinary mission:
   - `hello`
2. specialized mission:
   - `/specialized S02 explain the repeated-prefix runtime path briefly`
3. invalid specialized mission:
   - `/specialized TOOL please run tools`

Expected:
- visible route message in the chat for each run
- ordinary path returns deterministic placeholder text
- specialized path returns a result from `omlx-runtime`
- invalid specialized command returns out-of-scope without invoking the adapter

## Local artifacts
Phase 6 keeps artifacts local by default:
- run ledger:
  - `/home/christopherbailey/.local/state/orchestration-cockpit/run-ledger.jsonl`
- correlated `omlx-runtime` telemetry:
  - `/home/christopherbailey/.local/state/orchestration-cockpit/omlx-runtime-telemetry.jsonl`

These are local service artifacts, not repo-tracked runtime outputs.

## Rollback / cleanup
Stop the services:
```bash
sudo systemctl stop orchestration-cockpit-ui.service
sudo systemctl stop orchestration-cockpit-graph.service
```

Remove the installed units:
```bash
sudo rm -f /etc/systemd/system/orchestration-cockpit-graph.service
sudo rm -f /etc/systemd/system/orchestration-cockpit-ui.service
sudo systemctl daemon-reload
```

Verify ports are clear:
```bash
ss -ltn '( sport = :2024 or sport = :3030 )'
```

State/share directories remain by default:
- `/home/christopherbailey/.local/share/orchestration-cockpit/`
- `/home/christopherbailey/.local/state/orchestration-cockpit/`

Do not delete local state automatically unless explicitly requested.

## Later production-shaped path (deferred)
Do not treat `langgraph dev` as the long-term deployment shape.

Later productionization can move to:
- LangGraph standalone Agent Server / Docker image
- non-dev persistence/runtime backing such as Redis/Postgres or the then-current
  LangGraph deployment requirements
- formal UI hosting only after the local service contract proves durable
