# Agent Guidance: optillm-local

## Status
Experimental patch workspace only. Not deployed as a production service.
Do not deploy or expose ports without an explicit plan and approval.

## Non-negotiables (if revived)
- No secrets in git.
- No LAN exposure/port binding changes without an explicit plan.
- Follow `docs/foundation/orin-agx.md` and `docs/foundation/topology.md`.
- Keep changes isolated to experimental loopback-only workflows by default.
