# Implementation Plan

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

## Documentation Standardization Discovery Log (Living)

This section is the persistent record of findings gathered during repo-wide
documentation scoping. It is intentionally updated during discovery (before
implementation edits) so findings are not lost in chat context.

### Scope pass order
1. Monorepo root docs
2. `/docs` top-level docs + folders
3. `docs/foundation`
4. `docs/_core`

### Review state legend
- `draft` — captured but not yet normalized for owner review.
- `review-ready` — normalized and internally consistent; ready for owner review.
- `approved` — owner accepted; eligible for implementation edits.

---

### 1) Monorepo root matrix (review-ready)

| File | Role Class | Disposition | Rationale |
|---|---|---|---|
| `README.md` | Runtime orientation | KEEP (tighten scope) | Correct entrypoint; should stay short and link to canon. |
| `CONSTRAINTS.md` | Durable contract | KEEP (canonical) | Global non-negotiables for autonomy safety and sandbox boundaries. |
| `AGENTS.md` | Durable contract | KEEP (canonical) | Core agent behavior, verification mode, and guardrails. |
| `DOCS_CONTRACT.md` | Durable contract | KEEP (canonical) | Defines required docs architecture by scope (root/layer/service). |
| `SYSTEM_OVERVIEW.md` | Runtime orientation | KEEP (dedupe) | Useful layer map; should not duplicate detailed policy. |
| `TOPOLOGY.md` | Runtime orientation | KEEP (summary-only) | Keep as quick map that mirrors canonical topology docs. |
| `DIAGNOSTICS.md` | Runtime orientation | KEEP (ops-only) | Safe read-only triage command reference. |
| `INCIDENT_FLOW.md` | Runtime orientation | KEEP (canonical flow) | Clear escalation model by scope. |
| `NOW.md` | Operational state | KEEP (strict active-only) | Required by AGENTS; should contain only active + one NEXT UP. |
| `BACKLOG.md` | Operational state | KEEP (deferred-only) | Correct deferred-work sink. |
| `DESIGN_STATUS.md` | Temporal planning | MOVE/CONSOLIDATE (recommended) | Overlaps roadmap + decisions; temporal status should not drift at root. |
| `implementation_plan.md` | Temporal planning | KEEP (active planning artifact) | Current central execution plan for docs cleanup and standardization. |
| `SANDBOX_PERMISSIONS.md` | Durable policy (duplicated) | MERGE target (recommended) | Significant policy overlap with `AGENTS.md` + `DOCS_CONTRACT.md`. |

#### Root patterns identified
1. Durable policy is spread across multiple files (`CONSTRAINTS`, `AGENTS`, `DOCS_CONTRACT`, `SANDBOX_PERMISSIONS`).
2. Orientation docs are useful but partially duplicate canonical details.
3. Temporal artifacts live beside durable contracts at root (risk of drift).
4. Autonomy alignment exists, but lifecycle rules need stronger enforcement.

---

### 2) `/docs` top-level matrix (review-ready)

| Path | Current Role | Disposition | Rationale |
|---|---|---|---|
| `docs/PLATFORM_DOSSIER.md` | Platform canonical runtime truth | KEEP (authoritative) | Primary canonical ops state. |
| `docs/INTEGRATIONS.md` | Integration/routing canonical | KEEP (authoritative) | Core integration and routing truth. |
| `docs/ARCHITECTURE.md` | Platform architecture summary | KEEP (summary + dedupe) | Should remain concise and non-duplicative. |
| `docs/DECISIONS.md` | Decision index seed | KEEP + EXPAND | Currently minimal; good candidate for durable decision index. |
| `docs/EXTRACTION_MAP.md` | Extraction snapshot | MOVE to archive/deprecated class (recommended) | Temporal evidence artifact, not durable canon. |
| `docs/OPENCODE.md` | Client-specific run guide | KEEP (scoped guide) | Useful, but explicitly client-scoped. |
| `docs/OPENWEBUI_FEATURES.md` | UI feature/operator guide | KEEP (scoped guide) | Good reference; should remain non-canonical for platform state. |
| `docs/PLATFORM_CONSTRAINTS.md` | Constraint summary | MERGE target (recommended) | Overlaps root + foundation constraints docs. |
| `docs/_core/` | Documentation governance | KEEP (governance canonical) | Correct location for source-of-truth and change-rule control. |
| `docs/foundation/` | Durable architecture/ops references | KEEP | Correct durable extension/reference layer. |
| `docs/journal/` | Append-only temporal evidence | KEEP | Required historical chronology and rationale traceability. |
| `docs/archive/` | Historical frozen docs | KEEP | Correct home for retired docs; must stay non-canonical. |
| `docs/deprecated/` | Deprecated reference docs | KEEP | Correct deprecation sink. |
| `docs/prompts/` | Prompt artifacts/examples | KEEP (specialized support) | Non-canonical support domain. |

#### `/docs` top-level patterns identified
1. Canonical docs are mostly well placed.
2. Constraint/policy duplication still exists (`PLATFORM_CONSTRAINTS.md` overlap).
3. Temporal snapshots still sit close to canonical docs (`EXTRACTION_MAP.md`).
4. Service/client-specific docs need explicit scope labeling to avoid accidental canon.

---

### 3) `docs/foundation` matrix (review-ready)

#### Reviewed with deeper pass (current)

| File | Role | Disposition (review-ready assessment) | Notes |
|---|---|---|---|
| `docs/foundation/README.md` | Foundation navigation | KEEP (entrypoint) | Strong index; minor duplication in source list can be trimmed later. |
| `docs/foundation/autonomy-roadmap.md` | Durable strategy | KEEP (authoritative strategy) | Correct durable role and phase framing. |
| `docs/foundation/overview.md` | Architecture + operating summary | KEEP (dedupe with topology/integrations) | Useful but repeats some topology/OptiLLM specifics. |
| `docs/foundation/topology.md` | Canonical topology/endpoints | KEEP (authoritative) | Strong canonical role; contains dense mixed current/optional/planned details. |
| `docs/foundation/constraints-and-decisions.md` | Guardrails + core decisions | KEEP (authoritative) | Good canonical constraints baseline. |
| `docs/foundation/testing.md` | Verification playbook | KEEP (authoritative ops validation) | High value; could split by host/service later for clarity. |
| `docs/foundation/service-additions.md` | Change-contract checklist | KEEP | Strong guardrails for adding services and docs obligations. |
| `docs/foundation/operating-rhythm.md` | Process cadence | KEEP | Good operational rhythm; overlaps partially with AGENTS norms. |
| `docs/foundation/mcp-101.md` | Concept primer | KEEP (educational) | Useful orientation; non-canonical for runtime truth. |
| `docs/foundation/mcp-tools.md` | MCP status + guidance | KEEP | Useful but status statements need periodic freshness checks. |
| `docs/foundation/mcp-registry.md` | MCP registry template | KEEP | Correct canonical template role for tool registry design. |
| `docs/foundation/tool-contracts.md` | Tool I/O contracts | KEEP (authoritative for tool schemas) | Strong contract role; some status labels may lag implementation state. |

#### Additional reviewed files (review-ready pass)

| File | Role | Disposition (review-ready assessment) | Notes |
|---|---|---|---|
| `docs/foundation/git-submodules.md` | SCM workflow guide | KEEP (scoped operations guide) | Clear operational guidance; specific to contributor workflow, not runtime canon. |
| `docs/foundation/git-submodules-intellij.md` | IDE-specific SCM workflow | KEEP (scoped operations guide) | Useful companion to generic submodule doc; acceptable specialization. |
| `docs/foundation/golden-set-cleaning.md` | test fixture (cleaning) | KEEP (test asset) | Should be treated as benchmark input data, not architecture guidance. |
| `docs/foundation/golden-set-route.md` | test fixture (routing) | KEEP (test asset) | Good compact benchmark fixture. |
| `docs/foundation/golden-set-summarize.md` | test fixture (summarization) | KEEP (test asset) | Good benchmark data; could be grouped under explicit test-fixtures subsection later. |
| `docs/foundation/home-assistant-mcp.md` | integration reference | KEEP (scoped integration guide) | Useful external integration mapping; should remain clearly non-canonical for platform runtime state. |
| `docs/foundation/mlx-registry.md` | MLX control/registry contract | KEEP (authoritative) | High-value canonical contract for `mlxctl` and registry sync semantics. |
| `docs/foundation/onnx-evaluation.md` | evaluation plan | KEEP (temporal-planning within foundation) | Useful experimentation plan; should be marked as evaluation-only to avoid canon confusion. |
| `docs/foundation/optillm-techniques.md` | approach reference guide | KEEP (scoped guidance) | Strong usage guide; some entries are policy-sensitive and should track active OptiLLM deployment decisions. |
| `docs/foundation/orin-agx.md` | planned host profile | KEEP (planned-host profile) | Correctly marked planned; low drift risk if kept minimal. |
| `docs/foundation/ov-llm-server.md` | service overview bridge | KEEP (bridge doc) | Useful shorthand but should continue pointing to service-level canon for detailed behavior. |
| `docs/foundation/ov-model-onboarding.md` | model naming/onboarding rules | KEEP (conditional canonical) | Valuable when OpenVINO handles are active; currently risks partial drift against “not wired” states. |
| `docs/foundation/system-docs-db-schema.md` | future data schema spec | KEEP (design spec) | Strong design artifact; should remain explicitly future/planned until implemented. |

#### Foundation patterns identified
1. Foundation contains three mixed classes: **durable canon**, **operational guides**, and **experimental/planning docs**.
2. Golden sets are valuable but currently co-located with canon, reducing discoverability of “test fixture” status.
3. A few docs encode assumptions that may drift with deployment mode changes (especially OpenVINO/OptiLLM posture).
4. Foundation is high value overall; the main need is stronger labeling and sub-grouping, not broad deletion.

---

### 4) `docs/_core` governance matrix (review-ready)

| File | Role | Disposition (review-ready assessment) | Notes |
|---|---|---|---|
| `docs/_core/README.md` | Doc navigation hub | KEEP (authoritative navigation) | Clear read-order model for humans and agents. |
| `docs/_core/SOURCES_OF_TRUTH.md` | Truth hierarchy policy | KEEP (authoritative governance) | Critical conflict-resolution source. |
| `docs/_core/CHANGE_RULES.md` | Update obligations map | KEEP (authoritative governance) | Essential for preventing drift after changes. |
| `docs/_core/OPERATING_MODEL.md` | Execution loop model | KEEP | Strong process-level bridge from governance to execution. |
| `docs/_core/consistency_audit_2026-02.md` | Point-in-time audit ledger | KEEP (temporal evidence) | Should remain as dated audit artifact, not evergreen canon. |

#### `_core` patterns identified
1. `_core` is correctly functioning as governance control plane.
2. Read order + source hierarchy + change obligations are explicit and coherent.
3. Dated audit files belong here as evidence artifacts, with clear temporal labeling.

---

### 5) Layer-level + Ops/Planning/Script matrix (review-ready)

| Scope Path | Role | Disposition (review-ready assessment) | Notes |
|---|---|---|---|
| `layer-data/` | Layer docs boundary (data) | KEEP (review-ready) | Has layer-level `README.md` + `CONSTRAINTS.md`; aligns with sandbox intent. |
| `layer-gateway/` | Layer docs boundary (gateway) | KEEP (review-ready) | Has clear mission + constraints; includes handle/monitor boundaries. |
| `layer-inference/` | Layer docs boundary (inference) | KEEP (review-ready) | Layer docs present; `README.md` reference to `docs/ENSEMBLE_PARAMETER_SUPPORT.md` resolves in current tree. |
| `layer-interface/` | Layer docs boundary (interface) | KEEP (review-ready) | Layer docs present and concise; enforces gateway-only access. |
| `layer-tools/` | Layer docs boundary (tools) | KEEP (review-ready) | Layer docs present with local-only/tool-safety constraints. |
| `platform/ops/` | Operational scripts + units + templates | KEEP (review-ready, docs-gap) | Strong operational assets exist; no dedicated `platform/ops` narrative doc for governance/discoverability. |
| `next-projects/` | Temporal planning artifacts | KEEP (review-ready, temporal) | Correct location for forward plans; examples may drift from current handles/routing over time. |
| `scripts/` | Utility/validation entrypoints | KEEP (review-ready, docs-gap) | `validate_handles.py` is strong; no scripts index/readme for operator/agent discoverability. |

#### Layer/ops/planning/scripts patterns identified
1. Layer directories are structurally consistent at the layer-doc level (`README.md` + `CONSTRAINTS.md`).
2. `platform/ops` and `scripts` are operationally strong but under-documented as governance surfaces.
3. `next-projects` is correctly temporal but needs periodic staleness checks against current canonical docs.
4. No immediate missing-reference drift found in layer-level docs from the latest inventory pass.

---

### 6) Service-tier matrix (review-ready)

| Service Path | AGENTS | ARCHITECTURE | README | RUNBOOK | SERVICE_SPEC | TASKS | Disposition (review-ready assessment) | Notes |
|---|---|---|---|---|---|---|---|---|
| `layer-data/content-extract` | - | Y | Y | Y | Y | Y | KEEP (review-ready) | Good service-doc bundle; no service AGENTS file present. |
| `layer-data/vector-db` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete service-doc bundle with local AGENTS guidance. |
| `layer-gateway/litellm-orch` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Full bundle plus extended service docs. |
| `layer-gateway/optillm-local` | - | - | Y | - | Y | - | KEEP (needs-refresh) | Minimal docs footprint; no runbook/tasks/architecture docs currently present. |
| `layer-gateway/optillm-proxy` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete bundle with focused proxy guidance. |
| `layer-gateway/system-monitor` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete bundle; currently placeholder-oriented service scope. |
| `layer-gateway/tiny-agents` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete bundle + additional docs/scripts readmes. |
| `layer-inference/orin-llm-server` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete service-doc set with planned-host context. |
| `layer-inference/ov-llm-server` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete service-doc set + deep reference docs. |
| `layer-interface/open-webui` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete bundle with interface-layer scope constraints. |
| `layer-interface/voice-gateway` | - | Y | - | Y | Y | - | KEEP (needs-refresh) | Partial bundle; missing README/TASKS/AGENTS patterns vs peers. |
| `layer-tools/mcp-tools/web-fetch` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete bundle with scripts/docs sub-guides. |
| `layer-tools/searxng` | Y | Y | Y | Y | Y | Y | KEEP (review-ready) | Complete service-doc set; includes upstream app policy docs. |

#### Service-tier patterns identified
1. Service-level `SERVICE_SPEC.md` coverage exists for all 13 discovered services.
2. Most services follow the expected documentation bundle (`AGENTS`/`ARCHITECTURE`/`README`/`RUNBOOK`/`SERVICE_SPEC`/`TASKS`).
3. Two services are intentionally/accidentally sparse (`optillm-local`, `voice-gateway`) and should be treated as documentation-shape exceptions.
4. Service-tier discovery is now broad enough to support a second consistency audit against runtime/config/registry reality.

---

### 7) Coverage ledger snapshot (review-ready)

| Coverage Bucket | Current Scope | Priority in drift scoring | Notes |
|---|---|---|---|
| Active canonical/operational | Root + `docs` canonical + layer-level + service-tier + ops/templates/scripts that affect runtime | High | Primary target for cleanup waves and runtime consistency checks. |
| Scoped support/planning | `next-projects/*`, `docs/journal/*`, selected guidance docs | Medium | Kept in matrix coverage, but evaluated as temporal/support, not runtime canon. |
| Historical bucket | `docs/archive/*`, `docs/deprecated/*` | Low (excluded from primary drift scoring) | Included for coverage completeness; excluded from ops/architecture priority remediation. |

Coverage metrics snapshot:
- Total markdown files discovered repo-wide: `410`
- Historical bucket counts: `docs/archive` = `15`, `docs/deprecated` = `16`
- Service-tier count with `SERVICE_SPEC.md`: `13`

---

### Repo-wide synthesis (current)

#### Emerging organization model
- **Tier 1: Governance (rules of truth/change)**
  - `AGENTS.md`, `DOCS_CONTRACT.md`, `CONSTRAINTS.md`, `docs/_core/*`
- **Tier 2: Canonical platform truth**
  - `docs/PLATFORM_DOSSIER.md`, `docs/INTEGRATIONS.md`,
    `docs/foundation/topology.md`, `docs/foundation/constraints-and-decisions.md`,
    `docs/foundation/overview.md`
- **Tier 3: Scoped operator guides**
  - `docs/OPENCODE.md`, `docs/OPENWEBUI_FEATURES.md`, selected foundation how-to docs
- **Tier 4: Temporal/historical evidence**
  - `NOW.md`, `BACKLOG.md`, `docs/journal/*`, `docs/archive/*`, `docs/deprecated/*`, dated audits

#### Cleanup-wave direction (planning only)
1. **Wave A — Policy convergence:** reduce duplication across root policy docs.
2. **Wave B — Canonical boundary tightening:** ensure summary docs only point to canon.
3. **Wave C — Temporal relocation:** move snapshot-style docs out of canonical paths.
4. **Wave D — Foundation pruning:** split durable contracts from experimental/one-off guides.

#### Wave deliverables (planning only; no edits yet)
- **Wave A deliverables**
  - Single policy authority map across `CONSTRAINTS.md`, `AGENTS.md`, `DOCS_CONTRACT.md`, `SANDBOX_PERMISSIONS.md`, and `docs/PLATFORM_CONSTRAINTS.md`.
  - Merge/deprecate recommendations with explicit owner and migration notes.
- **Wave B deliverables**
  - Canonical-vs-summary annotations in root/docs entrypoints.
  - Pointer-first rewrites where summaries duplicate canonical details.
- **Wave C deliverables**
  - Relocation plan for temporal artifacts (`EXTRACTION_MAP`, similar snapshots) into archive/deprecated/journal tracks.
  - Lifecycle policy for new temporal docs (where they live, when they move).
- **Wave D deliverables**
  - Foundation taxonomy split: `canonical-contracts`, `operator-guides`, `evaluation-and-fixtures` (logical grouping first, path edits later by approval).
  - Drift watchlist for docs likely to desync with runtime posture.

#### Drift watchlist (highest leverage)
- `docs/PLATFORM_CONSTRAINTS.md` (duplicate constraints source)
- `SANDBOX_PERMISSIONS.md` (policy overlap with AGENTS/DOCS contract)
- `docs/EXTRACTION_MAP.md` (snapshot near canonical docs)
- `docs/foundation/ov-model-onboarding.md` (depends on active OpenVINO routing posture)
- `docs/foundation/optillm-techniques.md` (depends on active OptiLLM deployment posture)

#### Claim Reconciliation (Execution Readiness)

| Claim | Current statement in plan | Evidence source(s) | Reality status | Notes |
|---|---|---|---|---|
| Matrix coverage state | Root, `/docs`, `docs/foundation`, and `docs/_core` matrix scopes are documented | `implementation_plan.md` Discovery Log sections | confirmed | All four matrix scopes are present and populated. |
| Matrix status semantics | Matrix sections are review-ready prior to owner approval | Review state legend + matrix headings in this file | confirmed | Status language normalized to `review-ready` for owner review stage. |
| Policy duplication risk | Constraint/policy authority is duplicated across multiple docs | `CONSTRAINTS.md`, `AGENTS.md`, `DOCS_CONTRACT.md`, `SANDBOX_PERMISSIONS.md`, `docs/PLATFORM_CONSTRAINTS.md` | confirmed | Wave A remains required before cleanup implementation. |
| Temporal doc placement risk | Snapshot artifacts are near canonical docs and should be lifecycle-managed | `docs/EXTRACTION_MAP.md`, `docs/archive/*`, `docs/deprecated/*` | confirmed | Wave C relocation/lifecycle policy still needed. |
| OpenVINO posture-sensitive guidance | Some docs may drift based on whether OpenVINO is actively wired in LiteLLM | `docs/INTEGRATIONS.md`, `docs/PLATFORM_DOSSIER.md`, `docs/foundation/ov-model-onboarding.md` | needs-refresh | Re-verify at execution start against current router/config reality. |
| OptiLLM posture-sensitive guidance | Some docs may drift based on active OptiLLM deployment mode and usage semantics | `docs/INTEGRATIONS.md`, `docs/foundation/optillm-techniques.md`, service docs under `layer-gateway/optillm-*` | needs-refresh | Re-verify at execution start against active deployment posture. |
| Layer-level docs coverage | Layer directories have required layer-level docs structure | `layer-*/README.md`, `layer-*/CONSTRAINTS.md` | confirmed | Coverage is present for all five primary layers. |
| Layer-doc reference integrity | Layer-level references resolve to existing docs | `layer-inference/README.md` (`docs/ENSEMBLE_PARAMETER_SUPPORT.md`) | confirmed | Reference target exists in current tree (`layer-inference/docs/ENSEMBLE_PARAMETER_SUPPORT.md`). |
| Ops governance discoverability | `platform/ops` has clear narrative contract for operators/agents | `platform/ops/scripts/*`, `platform/ops/systemd/*`, `platform/ops/templates/*` | needs-refresh | Assets exist but no single ops narrative doc at `platform/ops` root. |
| Scripts discoverability contract | `scripts/` has index-level documentation | `scripts/validate_handles.py` | needs-refresh | Add scripts README/index in later cleanup wave if approved. |
| Next-project temporal hygiene | Planning docs are clearly non-canonical and periodically reconciled | `next-projects/TINYAGENTS_PLAN.md`, `next-projects/VOICE_ASSISTANT_V1.md` | needs-refresh | Temporal plans may carry stale examples; verify during implementation wave. |
| Service-tier coverage completeness | Every discovered service exposes `SERVICE_SPEC.md` | Service discovery across `layer-*` trees (`13` services) | confirmed | Service-tier matrix now has complete service-level baseline coverage. |
| Service-doc shape consistency | Services follow common doc bundle pattern | Service-level doc-presence matrix in this file | needs-refresh | `optillm-local` and `voice-gateway` are sparse vs common pattern; confirm intentionality. |
| Historical coverage policy | Archive/deprecated docs are tracked but de-prioritized | `docs/archive/*`, `docs/deprecated/*`, `docs/_core/SOURCES_OF_TRUTH.md` | confirmed | Historical bucket captured for completeness; excluded from primary runtime drift scoring. |

#### Consistency Audit Round 2 (active drift focus)

Round-2 audit scope (high-priority):
1. Canonical platform docs + root operational docs.
2. Layer-level docs + service-tier docs (excluding historical bucket from primary scoring).
3. Runtime truth evidence sources: router config, handles/registries, service specs/runbooks, ops systemd/scripts.

Round-2 initial drift candidates:
- Service-doc bundle sparsity exceptions: `layer-gateway/optillm-local`, `layer-interface/voice-gateway`.
- Ops governance discoverability gaps: `platform/ops` narrative doc absent, `scripts` index absent.
- Temporal plan staleness risk: `next-projects/*` examples vs active handles/routing/config posture.

Round-2 disposition policy:
- `critical/high`: active-runtime contradiction or unsafe operator guidance.
- `medium`: structural consistency/document-shape divergence.
- `low`: historical/support docs with non-operational drift.

#### Execution Gate (must be true before cleanup implementation)
- [ ] Owner reviewed all four matrix scopes.
- [ ] Owner reviewed service-tier matrix + coverage ledger + round-2 drift candidates.
- [ ] Claim reconciliation table has no unresolved `needs-refresh` items without explicit owner acceptance.
- [ ] Status language is normalized to review-ready across the Discovery Log.
- [ ] Cleanup wave order (A → B → C → D) is approved.
- [ ] Act-mode file edit scope for cleanup implementation is explicitly approved.

Status: review-ready; awaiting owner review before implementation edits.

Recon phase checkpoint: layer-level + service-tier + `platform/ops` + `next-projects` + `scripts` findings are captured; ready for owner review before remediation edits.
