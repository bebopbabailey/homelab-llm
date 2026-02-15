# Agent Sandboxing (Durable Policy)

Goal: make agent behavior predictable and safe as autonomy increases.

This is a policy/contract doc, not an implementation guide.

## Sources of truth
- Repo behavior: `AGENTS.md`
- Conflict resolution: `docs/_core/SOURCES_OF_TRUTH.md`
- Change obligations: `docs/_core/CHANGE_RULES.md`
- Sandbox scope rules: `SANDBOX_PERMISSIONS.md`
- Escalation: `INCIDENT_FLOW.md`
- Minimal docs required per layer/service: `DOCS_CONTRACT.md`

## Principles
- Prefer **read-only diagnosis** over action.
- Prefer **layer-scoped** fixes over cross-layer edits.
- Prefer **small reversible** edits and explicit validation.
- Treat **code execution** as privileged.

## Recommended execution boundary
For any agent that writes code:
- Use a **container sandbox** for executing generated code (snippet executor pattern).
- Do not mount secrets into the sandbox by default.
- Do not give the sandbox host networking unless explicitly required.

If a task requires secrets, privileged commands, or cross-host ops:
- escalate to an ops-capable agent with explicit scope and rollback, or
- require human approval and document the change.

## Scope tiers (suggested)
- Tier 0: Read-only (triage) - root overseer agent.
- Tier 1: Docs-only (codify drift) - canonical docs + service docs in scope.
- Tier 2: Service-local repair - one service directory + its deployed unit.
- Tier 3: Layer-wide repair - one `layer-*` with explicit boundaries.
- Tier 4: Ops/privileged - multi-host, restarts, deployment scripts.

## Success criteria for a sandboxed agent
An agent can be safely scoped to a layer/service when:
- the required docs bundle exists (see `DOCS_CONTRACT.md`)
- the layer has `DEPENDENCIES.md` and `RUNBOOK.md`
- verification commands are listed and do not require secrets to be printed
- rollback is obvious (git revert or service restart)

