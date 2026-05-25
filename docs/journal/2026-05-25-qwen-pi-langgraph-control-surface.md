# Qwen/Pi LangGraph Control Surface

## Summary
Added a first localhost-only LangGraph control path for the stable Pi/Qwen
scratch playground.

The cockpit now accepts `/pi <task>` and launches the existing launcher at
`/home/christopherbailey/pi-qwen-trials/current/run_pi_qwen.py`. The path is
scratch-only and returns pointers to Pi's own artifacts instead of copying run
output into the cockpit state directory.

## Runtime Contract
- Graph service remains `127.0.0.1:2024`.
- Stock Agent Chat UI remains `127.0.0.1:3030`.
- Qwen sidecar remains `127.0.0.1:4022`.
- Pi/Qwen runs remain under
  `/home/christopherbailey/pi-qwen-trials/current/runs/<run-id>/`.
- Supported operator commands:
  - `/pi <task>`
  - `/pi --temperature <0..2> --max-tokens <256..16384> <task>`

## Result
This is a control-surface slice, not a broader agent framework promotion.
No LiteLLM alias, OpenHands path, Open WebUI integration, MCP surface, Kanban
board, or real-repo targeting was added.

## Validation Notes
The expected acceptance is:
- orchestration-cockpit unit tests pass
- journal/docs checks pass
- `omlx-agent-gateway` health is ok
- one `/pi Fix the failing Python unittest suite.` graph invocation returns a
  successful Pi manifest with transcript, diff, and test-log paths
