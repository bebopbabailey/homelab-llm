# Implementation Plan

> Status: **COMPLETED (2026-02)** — canonical outcomes were captured in the audit ledger
> (`docs/_core/consistency_audit_2026-02.md`) and the consistency definition-of-done
> (`docs/_core/CONSISTENCY_DOD.md`). Keep this file at repo root as the historical
> plan record; use `implementation_plan_<topic>.md` for new efforts.

[Overview]
Audit and reconcile canonical documentation so platform statements match current runtime/config/registry reality.

This implementation will focus first on canonical platform documentation and root operational docs, then intentionally defer per-service documentation cleanup to a second phase. The immediate objective is to remove contradictory statements, stale aliases, and outdated operational assumptions that can mislead maintenance work (especially around routing, model handles, auth, and port ranges).

The plan uses source-of-truth precedence already defined in `docs/_core/SOURCES_OF_TRUTH.md`: registry/config/service specs and active runtime contracts outweigh older summaries. We will use those sources to build a documented inconsistency ledger, then apply targeted doc edits only where claims are materially wrong or ambiguous. Historical and archived docs will not be edited except to ensure they are clearly treated as historical.

This work is needed because several canonical files currently disagree on whether OpenVINO is wired, whether auth is enforced/planned, what MLX models occupy active boot ports, whether `json_logs` is enabled, and whether legacy `ov-*` aliases are active/deprecated. These inconsistencies create operational risk and increase the chance of incorrect changes.

[Types]
No runtime type system changes are required; this plan introduces a structured documentation-audit schema for consistency tracking only.

Define and use the following conceptual structures inside a new audit markdown (table-driven, not code-generated):

- `DocClaim`
  - `id: string` — stable claim identifier (e.g., `CLAIM-LITE-JSON-LOGS`)
  - `doc_path: string` — source document path
  - `section: string` — heading where the claim appears
  - `claim_text: string` — exact or near-exact claim
  - `domain: enum` — one of `routing`, `auth`, `ports`, `models`, `health`, `exposure`, `status`

- `Evidence`
  - `source_path: string` — authoritative source path (config/registry/spec)
  - `evidence_type: enum` — `config`, `registry`, `service_spec`, `runbook`, `ops_rule`
  - `observed_value: string` — canonical value currently present

- `InconsistencyRecord`
  - `severity: enum` — `critical`, `high`, `medium`, `low`
  - `disposition: enum` — `fix_now_phase1`, `defer_phase2`, `archive_only`, `needs_owner_decision`
  - `proposed_resolution: string` — exact wording or direction for correction
  - `touch_files: string[]` — docs to update

Validation rules for this schema:
- Every `DocClaim` must map to at least one `Evidence` entry.
- Every `InconsistencyRecord` must include an explicit disposition.
- Phase-1 scope may only include canonical/root docs (no `layer-*` edits except references).

[Files]
The plan updates canonical/root docs and introduces one audit ledger file to track each inconsistency-to-evidence decision.

Detailed breakdown:

- New files to be created
  - `docs/_core/consistency_audit_2026-02.md`
    - Purpose: machine-readable-for-humans ledger of mismatched claims, authoritative evidence, severity, and fix disposition.

- Existing files to be modified (Phase 1: canonical + root)
  - `docs/INTEGRATIONS.md`
    - Align `json_logs` statement with current `router.yaml` (`false` currently).
    - Align auth wording with actual gateway requirement state.
    - Remove/adjust stale alias claims (`boost-deep`, `x1-x4`) not present in active router config.
    - Reconcile OpenVINO wiring statement with canonical routing reality.
  - `docs/PLATFORM_DOSSIER.md`
    - Resolve contradictory OpenVINO alias wording (`uses ov-*` vs `ov-* deprecated`).
    - Align boot ensemble model labels with current router/handle reality (port 8101 model).
    - Confirm OptiLLM local 4042 status wording consistency.
  - `docs/foundation/topology.md`
    - Align boot ensemble names with current router/registry state.
    - Ensure port-range and endpoint narratives match dossier and routing docs.
  - `docs/foundation/overview.md`
    - Align specialist backend statements with current canonical integration status (especially OpenVINO and OptiLLM-local framing).
  - `docs/ARCHITECTURE.md`
    - Align high-level backend claims with canonical integration reality and avoid stale alias assumptions.
  - `README.md`
    - Correct stale statements about OpenVINO offline status and experimental aliases if no longer true.
  - `TOPOLOGY.md`
    - Align Studio MLX port range summary to canonical 8100–8119 team and 8120–8139 experimental usage (if still canonical).
  - `SYSTEM_OVERVIEW.md`
    - Clarify “everything through LiteLLM” statement where direct OptiLLM usage is intentionally documented.
  - `NOW.md`
    - Update active task to this documentation consistency cleanup during execution.

- Existing files to be modified (Phase 2: deferred per user direction)
  - `layer-gateway/litellm-orch/README.md`
  - `layer-gateway/litellm-orch/SERVICE_SPEC.md`
  - `layer-gateway/litellm-orch/ARCHITECTURE.md`
  - `layer-gateway/litellm-orch/DEV_CONTRACT.md`
  - `layer-gateway/litellm-orch/TASKS.md`
  - Related service docs that still reference deprecated alias families.

- Files to be deleted or moved
  - None.

- Configuration file updates
  - No runtime config edits in this task; configuration files are read as evidence only.

[Functions]
No production/runtime function changes are required; only optional audit-helper script functions are proposed for later automation.

Detailed breakdown:

- New functions (optional, only if automation is approved later)
  - `collect_claims(paths: list[str]) -> list[DocClaim]`
    - File path: `scripts/docs_consistency_audit.py` (optional future addition)
    - Purpose: parse markdown sections and detect known claim patterns.
  - `load_authoritative_evidence() -> dict[str, Evidence]`
    - File path: `scripts/docs_consistency_audit.py`
    - Purpose: normalize evidence from router, handles, and registry files.
  - `compare_claims_to_evidence(...) -> list[InconsistencyRecord]`
    - File path: `scripts/docs_consistency_audit.py`
    - Purpose: generate mismatch report.

- Modified functions
  - None in Phase 1.

- Removed functions
  - None.

[Classes]
No class changes are required for this documentation-focused implementation.

Detailed breakdown:

- New classes
  - None.

- Modified classes
  - None.

- Removed classes
  - None.

[Dependencies]
No dependency changes are required for Phase-1 documentation reconciliation.

No new packages, lockfile updates, or version changes should be introduced. If optional audit automation is pursued later, it should use standard library only unless explicit approval is given.

[Testing]
Verification will use deterministic command-based checks to prove docs now match canonical config/registry/service sources.

Test requirements and validation strategy:

- Pre/post mismatch scans
  - Use targeted grep checks for known drift terms (`ov-*`, `json_logs`, `LITELLM_PROXY_KEY`, `boost-deep`, `x1-x4`, stale port ranges/models).
- Source-of-truth checks
  - Validate handles/registry consistency via `python3 scripts/validate_handles.py`.
  - Cross-check active router values from `layer-gateway/litellm-orch/config/router.yaml`.
- Documentation contract sanity
  - Ensure updated canonical docs continue to point to proper sources of truth and do not conflict with `docs/_core/SOURCES_OF_TRUTH.md`.
- Outcome reporting
  - Provide per-file change summary with exact corrected claims.
  - Record any intentionally deferred items in the audit ledger as Phase 2.

[Implementation Order]
Implement in a ledger-first sequence: establish evidence, apply canonical fixes, then verify and stage deferred per-service cleanup.

1. Create `docs/_core/consistency_audit_2026-02.md` with claim/evidence/disposition table seeded from currently identified mismatches.
2. Reconcile canonical docs in this order: `docs/INTEGRATIONS.md` → `docs/PLATFORM_DOSSIER.md` → `docs/foundation/topology.md` → `docs/foundation/overview.md` → `docs/ARCHITECTURE.md`.
3. Reconcile root summaries: `README.md`, `TOPOLOGY.md`, `SYSTEM_OVERVIEW.md` so they mirror canonical docs.
4. Update `NOW.md` to reflect the active docs cleanup task and immediate next-up.
5. Run verification commands (`scripts/validate_handles.py`, targeted grep assertions) and correct any residual contradictions.
6. Produce final inconsistency report with:
   - fixed items (Phase 1 complete),
   - deferred items (Phase 2 per-service docs),
   - open owner decisions if any.

## Autonomy Alignment Addendum

### Why this addendum
The original plan correctly prioritizes documentation consistency. This addendum
aligns that work to the clarified long-term objective: documentation must support
safe, scalable autonomous operation (not just factual correctness).

### Revised objective
Preserve Phase-1 canonical consistency cleanup while ensuring docs function as an
operating system for scoped agents: truth discovery, allowed actions, verification,
and escalation.

### Scope refinement
- Keep Phase 1 unchanged: canonical/root factual consistency cleanup.
- Add operability requirements so agents can reliably determine:
  1) what is true,
  2) what is allowed,
  3) how to verify,
  4) when to rollback/escalate.
- Keep Phase 2 deferred: per-service (`layer-*`) doc cleanup.

### Durable document roles
- `docs/foundation/autonomy-roadmap.md` — durable capability strategy.
- `NOW.md` — active execution only.
- `BACKLOG.md` — deferred work only.
- `docs/DECISIONS.md` — architecture/policy decisions.
- Canonical runtime truth remains in:
  - `docs/PLATFORM_DOSSIER.md`
  - `docs/foundation/topology.md`
  - `docs/INTEGRATIONS.md`
  - service specs + registry/config files.

### Additional acceptance criteria (agent-operability)
This plan is complete only if:
1. **Truth discoverability:** canonical sources are unambiguous.
2. **Scope enforceability:** allowable file/service boundaries are explicit.
3. **Verification determinism:** required checks and expected signals are documented.
4. **Failure handling:** rollback/escalation conditions are explicit.
5. **State hygiene:** active vs deferred work is clearly separated.

### Two-track execution model
- **Track A — Consistency:** remove factual drift in canonical/root docs.
- **Track B — Operability:** document autonomy controls (risk tiers, gate checks,
  escalation semantics).

Track A remains the gating prerequisite for safe implementation.

### Implementation order adjustment
Insert after original Step 3:
- **Step 3.5 (new):** validate document-role alignment across roadmap/NOW/BACKLOG/
  decisions docs before final verification.

### Handoff contract for future coding agents
Every implementation task should include:
- explicit source-of-truth references,
- allowed file boundaries,
- FAST/FULL verification command list,
- rollback/escalation condition,
- post-change updates to `NOW.md`/`BACKLOG.md` when needed.

## Audit consolidation note

The canonical consistency-audit discovery, matrices, claim reconciliation, and
round disposition now live in:

- `docs/_core/consistency_audit_2026-02.md`

`implementation_plan.md` is intentionally implementation-focused only.
