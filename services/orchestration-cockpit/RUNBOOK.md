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

## Local config
Copy the service env template locally and keep it out of git:
```bash
cp services/orchestration-cockpit/.env.example services/orchestration-cockpit/.env
```

Expected local env values:
- `OMLX_RUNTIME_BASE_URL=http://127.0.0.1:8129`
- `OMLX_RUNTIME_BEARER_TOKEN=...`
- `OMLX_RUNTIME_MODEL=Qwen3-4B-Instruct-2507-4bit`
- `ORCHESTRATION_COCKPIT_ARTIFACT_DIR=/tmp/orchestration-cockpit-phase5`
- `PYTHONPATH=./src:../omlx-runtime/src`
- `LANGSMITH_API_KEY=...` only if `langgraph dev` still requires it locally

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
- launch from the service root or use the wrapper so `PYTHONPATH` resolves
  `./src:../omlx-runtime/src` for the local checkout layout
- the graph must not compile with a custom checkpointer; `langgraph dev`
  rejects that shape and manages persistence itself

## Agent Chat UI (not vendored)
Option 1: local scaffold
```bash
npx create-agent-chat-app --project-name orchestration-cockpit-ui
cd orchestration-cockpit-ui
cp /home/christopherbailey/homelab-llm/services/orchestration-cockpit/ui/.env.example .env.local
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

## Local service ownership target
Phase 5 defines, but does not require enabling, these repo-managed unit targets:
- `platform/ops/systemd/orchestration-cockpit-graph.service`
- `platform/ops/systemd/orchestration-cockpit-ui.service`

Expected env file ownership:
- graph unit: `/etc/orchestration-cockpit/graph.env`
- UI unit: `/etc/orchestration-cockpit/ui.env`

Expected installed host units:
- `/etc/systemd/system/orchestration-cockpit-graph.service`
- `/etc/systemd/system/orchestration-cockpit-ui.service`

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
Phase 5 keeps artifacts local by default:
- run ledger:
  - `/tmp/orchestration-cockpit-phase5/run-ledger.jsonl`
- correlated `omlx-runtime` telemetry:
  - `/tmp/orchestration-cockpit-phase5/omlx-runtime-telemetry.jsonl`

These are local service artifacts, not repo-tracked runtime outputs.

## Later production-shaped path (deferred)
Do not treat `langgraph dev` as the long-term deployment shape.

Later productionization can move to:
- LangGraph standalone Agent Server / Docker image
- non-dev persistence/runtime backing such as Redis/Postgres or the then-current
  LangGraph deployment requirements
- formal UI hosting only after the local service contract proves durable
