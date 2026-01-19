# Incident Flow (Agent Escalation)

This describes how the system responds to failures.

## Roles
- **Root agent (read‑only)**: triage, diagnosis, routing
- **Layer agent (read/write in layer)**: layer‑specific remediation
- **Service agent (full in service)**: code/config fixes + restart

## Flow
1) **Monitor detects fault** (health check failure, error log, latency spike).
2) **Root agent** runs read‑only diagnostics and decides scope:
   - service‑local
   - layer‑wide
   - cross‑layer
3) **Root agent dispatches** to the smallest responsible agent:
   - service agent if isolated
   - layer agent if systemic
4) **Service/layer agent** performs fix and reports outcome.
5) **Root agent** validates recovery with health checks.

## Escalation guardrails
- Root agent never modifies services directly.
- Layer agent never modifies other layers.
- Service agent never changes ports/bindings without approval.
