# Agent Chat UI wrapper

This service does **not** vendor the full Agent Chat UI app into this repo.

Use either:
- `npx create-agent-chat-app`, or
- a separate local checkout of `langchain-ai/agent-chat-ui`

Required local connection settings:
- Graph ID: `operator-cockpit`
- Deployment URL: `http://127.0.0.1:2024`
- Agent Chat UI local dev port: `127.0.0.1:3030`

Copy `.env.example` to the UI project as `.env.local`.

Local launch posture:
- run the UI only
- do not use the scaffold's root `pnpm dev` command
- the root scaffold script also launches its own agent server on `:2024` and
  defaults the web app to `:3000`
- for this repo, point the web app at the existing local LangGraph server on
  `127.0.0.1:2024` and bind the UI itself to `127.0.0.1:3030`

Phase 5 ownership rule:
- keep Agent Chat UI stock
- do not fork or vendor it unless the stock local integration proves
  insufficient
- the repo owns only config, env templates, runbook steps, and service wrappers

Phase 6 ownership target:
- supported external UI root:
  - `/home/christopherbailey/.local/share/orchestration-cockpit/agent-chat-ui`
- installed runtime env:
  - `/etc/orchestration-cockpit/ui.env`
- systemd unit target:
  - `orchestration-cockpit-ui.service`
- the UI remains a localhost-only dev-mode `next dev` service in this phase; it
  is not a production Next.js deployment
- the supported host env should pin a durable launcher path, preferably the
  scaffold-local `next` binary, for example:
  - `ORCHESTRATION_COCKPIT_NEXT_BIN=/home/christopherbailey/.local/share/orchestration-cockpit/agent-chat-ui/apps/web/node_modules/.bin/next`
- if that is unavailable, fall back to `corepack`, for example:
  - `ORCHESTRATION_COCKPIT_COREPACK_BIN=/home/christopherbailey/.volta/tools/image/node/24.13.0/bin/corepack`

LangSmith note:
- Agent Chat UI itself does **not** require a LangSmith API key for local
  server use.
- A LangSmith API key may still be required by `langgraph dev` as a local
  tooling prerequisite. That key is local-only and is not part of cockpit auth.
