# Gateway Layer Constraints

## Hard constraints
- Must remain routing/observability only (no inference).
- Clients must call LiteLLM only; do not bypass the gateway.
- OptiLLM proxy may call MLX endpoints directly when configured; avoid routing loops.
- Optimization proxies (OptiLLM) must bind to localhost and sit behind LiteLLM.
- Do not change port bindings without a migration plan.

## System monitor boundaries
- **Read‑only** health checks and status queries only.
- **No direct restarts** from the monitor.
- Escalation via bulletin/DB entry (planned in system docs DB).

## Sandbox permissions
- Read: `layer-gateway/*`
- Write: gateway configs + docs only
- Execute: restart gateway services only (LiteLLM, OptiLLM, system monitor)
- Forbidden: direct inference changes, port reuse without plan

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.
