# Sources of Truth

This repo uses multiple layers of truth. When sources disagree, resolve conflicts using the rule at the end of this document.

## Authoritative
Current, canonical statements of the system, its contracts, and its integration surface.
- Platform-level canon:
    - `docs/PLATFORM_DOSSIER.md`
    - `docs/foundation/topology.md`
    - `docs/foundation/studio-scheduling-policy.md`
    - `docs/foundation/constraints-and-decisions.md`
    - `docs/foundation/overview.md`
    - `docs/foundation/runtime-planes.md`
    - `docs/INTEGRATIONS.md`
    - `docs/foundation/mlx-registry.md`
    - `docs/foundation/runtime-lock.md`
    - `docs/foundation/ov-llm-server.md`
    - `docs/foundation/orin-agx.md`
- Repo-local OpenCode control plane:
    - `opencode.json`
    - `.opencode/instructions/repo-baseline.md`
    - `.opencode/agents/*.md`
    - `.opencode/skills/*/SKILL.md`
    - `docs/OPENCODE.md` (supporting narrative doc for the repo-local control surface)
- Registry/template data (prefer data over summaries):
    - `platform/registry/services.jsonl`
    - `platform/registry/handles.jsonl`
    - `platform/registry/models.jsonl`
    - `platform/registry/lexicon.jsonl`
    - `platform/registry/README.md`
    - `platform/ops/templates/mcp-registry.json`
    - `platform/ops/runtime-lock.json`
- Per-service canon (most specific truth for a service):
    - the service root declared in `platform/registry/services.jsonl`
    - `<service-root>/SERVICE_SPEC.md`
    - (supporting) `<service-root>/ARCHITECTURE.md`, `RUNBOOK.md`, `AGENTS.md`, `CONSTRAINTS.md`
- Layer taxonomy/navigation only:
    - `layer-*/README.md`
    - These are non-authoritative indexes. They should not carry service
      contracts, runtime rules, or operational truth that duplicates service or
      platform docs.

## Operational
How to run, test, or validate the current system.
- `docs/foundation/testing.md`
- `docs/foundation/service-additions.md`
- `docs/foundation/service-catalog.md`
- `DOCS_CONTRACT.md`
- `CONSTRAINTS.md`
- `SYSTEM_OVERVIEW.md`
- `TOPOLOGY.md`
- `DIAGNOSTICS.md`
- `INCIDENT_FLOW.md`
- `scripts/validate_handles.py`
- `SANDBOX_PERMISSIONS.md`

## Planning/Temporal
Time-bound intent, priorities, and work-in-progress notes.
- `NOW.md`
- `BACKLOG.md`
- `DESIGN_STATUS.md`
- `SCRATCH_PAD.md`
- `next-projects/*`
- `docs/journal/*`

## Historical
Archived or deprecated material kept for reference only.
- `docs/archive/00-EXTRACTION_MAP.md`
- `docs/archive/01-PLATFORM_TOPOLOGY.md`
- `docs/archive/02-PORTS_ENDPOINTS_REGISTRY.md`
- `docs/archive/03-SERVICE_INVENTORY.md`
- `docs/archive/04-INTEGRATIONS_LITELLM.md`
- `docs/archive/05-INTEGRATIONS_OPENWEBUI.md`
- `docs/archive/06-INTEGRATIONS_OPENVINO.md`
- `docs/archive/07-SECURITY_BOUNDARIES.md`
- `docs/archive/08-CONSTRAINTS.md`
- `docs/archive/09-PHASE_PLAN_TINYAGENTS.md`
- `docs/archive/10-TASKS_TINYAGENTS.md`
- `docs/archive/11-TEST_PLAN_SMOKES.md`
- `docs/archive/12-DECISIONS_LOG.md`
- `docs/archive/13-EXTRACTION_MAP_2026-02.md`
- `docs/archive/2026-02-onnx-evaluation.md`
- `docs/archive/2026-02-golden-set-cleaning.md`
- `docs/archive/2026-02-golden-set-route.md`
- `docs/archive/2026-02-golden-set-summarize.md`
- `docs/archive/DECISIONS.md.old`
- `docs/archive/EXTRACTION_MAP.md.old`
- `docs/archive/INTEGRATIONS.md.old`
- `docs/archive/PLATFORM_CONSTRAINTS.md.old`
- `docs/archive/PLATFORM_DOSSIER.md.old`
- `docs/archive/TINYAGENTS_PLAN.md.old`
- `docs/deprecated/README.md`
- `docs/deprecated/benny-model-onboarding.md`
- `docs/deprecated/prompts/benny/`
- `docs/DECISIONS.md`

## Conflict Rule
If sources disagree, prefer the highest category in this order: Authoritative → Operational → Planning/Temporal → Historical. Within a category, prefer the more specific scope (service-level `SERVICE_SPEC.md` beats global docs; registry data beats summaries).
