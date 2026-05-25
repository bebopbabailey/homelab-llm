# Orchestration Cockpit Safari Tunnel

## Summary
Added a configurable LangGraph dev-server tunnel switch for Safari use with
hosted LangSmith Studio.

Safari blocks the hosted Studio page from using plain-HTTP localhost Agent
Server URLs. The cockpit wrapper now honors
`ORCHESTRATION_COCKPIT_GRAPH_TUNNEL=true` and appends `--tunnel` to
`langgraph dev`.

## Runtime
- Local Agent Server remains `127.0.0.1:2024`.
- Agent Chat UI remains `127.0.0.1:3030`.
- Tunnel mode prints an HTTPS Studio URL to
  `journalctl -u orchestration-cockpit-graph.service`.
- The tunnel is only a development convenience for Studio/Safari and does not
  change the cockpit's repo-owned API contract.
