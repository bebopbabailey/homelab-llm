# Codex ↔ OpenHands Harness Pilot — Phased Implementation Plan

## Summary

Build a private, repo-local harness for agentic coding experiments before promoting OpenHands + preferred model backends into the main experiment loop.

This project is **not** OpenHands itself.
This project is the **laboratory** around it:

- a controlled execution surface
- a transcript and event capture layer
- a phase/task/gate workflow
- a run ledger for evals and postmortems
- a thin web UI for reviewing full agent conversations
- a stable bridge layer where Codex can help prepare the system before OpenHands becomes the primary experimental executor

The first meaningful success is **not** autonomy.
The first meaningful success is:

> run one bounded coding task through the harness, capture the full trajectory, validate it, and review it comfortably in a browser.

---

## Why this exists

This pilot should produce three outputs at once:

1. **A usable private tool**
   - readable browser chat/log view for long coding-agent runs
   - better than squinting at mobile terminal output

2. **A reusable experiment harness**
   - runs, transcripts, validations, approvals, diffs, outcomes
   - comparable across Codex and later OpenHands runs

3. **A high-value personal dataset**
   - planning traces
   - approval decisions
   - validation results
   - failure modes
   - “how Bebop actually works” operator data

---

## Goals

- Create a private web app for viewing and managing coding-agent runs.
- Capture useful structured data from every run without building a giant telemetry monster.
- Use Codex first for preparation, scaffolding, and early execution traces.
- Prepare a clean runway for OpenHands to become the next executor inside the harness.
- Preserve the repo’s existing discipline: scoped work, verification, and `NOW.md` updates.

---

## Non-goals (for this pilot)

- No generalized multi-agent orchestration platform.
- No full Open WebUI bridge in v1.
- No public deployment.
- No fine-tuning pipeline in this pilot.
- No heavy observability stack beyond what is needed for useful trace capture.
- No “autonomous software factory” ambitions in v1.

---

## Operating principle

Prefer **meaty vertical slices** over infrastructure yak-shaving.

When choosing between:
- building more platform
- or proving the next end-to-end slice

pick the slice.

---

## Core product definition

The harness owns these concepts:

- **Project**
- **Phase**
- **Task**
- **Run**
- **Thread**
- **Approval**
- **Artifact**
- **Validation Result**
- **Closeout**

The UI is a chat-like interface, but the system is really an **execution ledger with conversation views**.

---

## Data to capture

Capture only data that helps evaluation, replay, review, or later adaptation.

### Required per run
- run id
- timestamp
- executor (`codex-cli`, `codex-app-server`, `openhands`, etc.)
- model / lane
- repo / path
- phase
- task
- initial prompt
- follow-up prompts
- assistant messages
- tool / command events
- file edit events
- diff summary
- validation commands
- validation outputs
- approval events
- final outcome
- operator notes
- status (`success`, `partial`, `failed`, `aborted`)

### Nice-to-have
- token usage
- elapsed time
- exit codes
- simple rubric score
- tags (`planning`, `patch`, `research`, `refactor`, etc.)

### Explicitly avoid in pilot
- massive low-level telemetry exhaust
- packet-level traces
- screen scraping
- overbuilt analytics before useful runs exist

---

## Storage model

Start boring.

### v1 storage
- SQLite database for run metadata
- filesystem artifact store for:
  - raw JSONL
  - rendered markdown/html
  - diff files
  - validation logs
  - exported closeouts

### Suggested paths
- `var/codex-harness/app.db`
- `var/codex-harness/runs/<run-id>/`
- `var/codex-harness/runs/<run-id>/events.jsonl`
- `var/codex-harness/runs/<run-id>/answer.md`
- `var/codex-harness/runs/<run-id>/validation.log`
- `var/codex-harness/runs/<run-id>/closeout.md`

---

## UI principles

The app should be optimized for **reading long agent work**, not for looking flashy.

### Required UI surfaces
- run list
- run detail page
- full transcript view
- event timeline
- artifact panel
- validation results panel
- phase/task metadata panel
- resume / rerun / export actions

### UX rules
- long messages must be easy to scroll
- command executions must be collapsible
- diffs and validation logs must not drown the conversation
- conversation and execution timeline must be clearly separated
- mobile reading must be first-class

---

## Codex role in this project

Codex is the **preparation worker** first.

Use Codex to:
- refine the implementation plan
- scaffold the app
- generate schemas and storage code
- build the importer for JSONL traces
- implement the first transcript UI
- create validation helpers
- write project documentation
- generate closeout summaries
- help build the OpenHands integration seam

Do **not** require OpenHands for the first valuable result.

---

## OpenHands role in this project

OpenHands is the **next executor under test**, not the product.

OpenHands enters after the harness can already:
- store runs
- show transcripts
- attach validations
- produce closeouts
- compare outcomes across executions

OpenHands should slot into the harness as one executor among others.

---

## Phase plan

---

# Phase 0 — Charter, scope, and run contract

## Objective
Define the pilot sharply enough that Codex can implement it without drifting.

## Deliverables
- this implementation plan in repo root
- `BACKLOG.md` entries for deferred ideas
- project-specific `NOW.md` update when work begins
- run object schema
- artifact directory layout
- clear success/failure states
- initial task taxonomy
- minimal scoring rubric

## Gates
- one page defines what a run is
- one page defines what data is required per run
- one page defines what “pilot success” means
- deferred ideas are pushed out of active scope

## Notes
This phase is complete when the experiment is narrow enough that implementation can begin without architecture debate every hour.

---

# Phase 1 — Thin capture spine

## Objective
Build the smallest possible backend that can create, persist, and inspect runs.

## Deliverables
- app skeleton
- SQLite schema
- run creation endpoint
- artifact directory creation
- basic run list endpoint
- basic run detail endpoint
- filesystem-backed artifact storage
- health check
- minimal config file

## Gates
- a run can be created manually without any agent integration
- run metadata persists across restarts
- artifact paths are stable and human-readable
- developer can inspect a run with one command and one browser page

## Out of scope
- fancy UI
- auth complexity
- OpenHands integration
- Open WebUI bridge

---

# Phase 2 — Codex non-interactive ingestion

## Objective
Make Codex the first real executor feeding the harness.

## Deliverables
- wrapper for `codex exec --json`
- JSONL ingestion pipeline
- event normalizer
- mapping from Codex events to internal run events
- storage of raw JSONL + normalized event rows
- final answer extraction
- command execution capture
- file change capture
- validation command attachment
- browser transcript rendering from captured data

## Gates
- a single Codex run can be launched from the harness
- the raw JSONL is preserved
- the browser shows the conversation and event timeline
- long plans are readable without terminal dependence
- at least 3 seeded prompts produce reviewable transcripts

## Notes
This is the first “meaty bits” phase.
Do not delay this to build generic abstractions.

---

# Phase 3 — Human review and closeout workflow

## Objective
Turn raw captured runs into something useful for decision-making and later adaptation.

## Deliverables
- operator notes field
- approval record model
- validation command panel
- pass/fail/partial outcome selection
- closeout markdown generator
- exportable run bundle
- tag support (`planning`, `patch`, `debug`, `refactor`, etc.)

## Gates
- every run can be closed out consistently
- a failed run still produces a useful artifact bundle
- a run can be reviewed later without replaying terminal output
- operator can answer “what happened and was it good?” in under 2 minutes

## Notes
This is where the data becomes useful instead of merely existing.

---

# Phase 4 — Phase/task/gate-aware UI

## Objective
Make the harness reflect your actual working style instead of being a generic chat log.

## Deliverables
- phase metadata on runs
- task metadata on runs
- `current task`, `up next`, `next phase` fields
- phase filter in run list
- gate checklist support
- `NOW.md` helper/export for current active work
- project dashboard with:
  - active phase
  - current task
  - recent runs
  - pending gates

## Gates
- the UI can show work in the same shape you reason about it
- a run is clearly attached to a phase and task
- active work can be summarized into `NOW.md` format without manual archaeology

## Notes
This is where the tool becomes “yours” rather than generic.

---

# Phase 5 — Validation-first experiment loop

## Objective
Make runs comparable and useful as experiments.

## Deliverables
- validation profile support
- run templates for:
  - planning
  - patching
  - debugging
  - review
- basic rubric scoring
- seeded benchmark task set
- compare-runs view
- rerun action with same prompt/task metadata
- per-run verdict fields:
  - correctness
  - completeness
  - policy fit
  - operator usefulness

## Gates
- at least 10 benchmark tasks exist
- at least 2 runs on the same task can be compared sanely
- operator can identify whether a model or executor improved
- manual fixes can be turned into future benchmark cases

## Notes
Do not overbuild “evaluation infrastructure.”
Keep it concrete and task-linked.

---

# Phase 6 — OpenHands preparation seam

## Objective
Prepare the harness to host OpenHands without turning this project into OpenHands implementation work.

## Deliverables
- executor abstraction just sufficient for a second backend
- OpenHands run record shape
- OpenHands config contract page
- mapping for:
  - workspace path
  - model/lane
  - validation profile
  - artifact capture
- explicit list of what OpenHands events/results must be captured
- “ready for OpenHands” checklist

## Gates
- adding OpenHands requires no rewrite of existing Codex capture
- the harness knows what it expects from an OpenHands run
- the interface between harness and OpenHands is documented and testable

## Notes
This is a preparation phase, not a full OpenHands integration phase.

---

# Phase 7 — First OpenHands execution pass

## Objective
Run the first bounded OpenHands task through the harness.

## Deliverables
- OpenHands executor adapter
- launch/resume flow
- run record + artifact storage
- transcript or event rendering sufficient for review
- validation output attachment
- first side-by-side Codex vs OpenHands comparison

## Gates
- one bounded repo task runs end-to-end
- transcript is reviewable in the browser
- validation results attach cleanly
- comparison with Codex run is possible

## Success condition
The harness proves it can host OpenHands as an executor under the same review model.

---

# Phase 8 — Pilot evaluation and promotion decision

## Objective
Judge whether the harness is useful enough to keep and whether OpenHands should be promoted deeper into the lab.

## Deliverables
- pilot report
- benchmark summary
- failure taxonomy
- operator usability notes
- “keep / revise / retire” recommendation
- next-phase recommendation

## Gates
- clear list of what worked
- clear list of what wasted time
- clear recommendation for:
  - Codex continuing role
  - OpenHands next scope
  - local model trial scope
  - Open WebUI bridge timing

---

## Benchmark task buckets

Start with 3 buckets only.

### Bucket A — Planning
Examples:
- implementation plan
- migration plan
- hardening plan
- rollout checklist

### Bucket B — Patch loop
Examples:
- add a narrow feature
- fix a small bug
- write missing docs for touched files
- adjust a config contract

### Bucket C — Review / synthesis
Examples:
- summarize repo state
- compare two docs for drift
- review a run and produce closeout
- inspect a patch and propose corrections

---

## Minimal scoring rubric

Each run gets a 1–5 score on:

- task completion
- correctness
- validation quality
- transcript usefulness
- operator trust
- reuse value

Add a short free-text note:
- what helped
- what wasted time
- what should become a benchmark next

---

## Success criteria for the pilot

The pilot succeeds if all of the following are true:

- long Codex outputs are readable in-browser
- at least 10 useful runs are captured
- at least 3 tasks are rerun and compared
- closeout quality is good enough to learn from failures
- OpenHands can be introduced through a documented seam instead of guesswork
- the harness clearly improves operator workflow

---

## Failure criteria for the pilot

The pilot fails if any of the following dominate:

- too much time spent on plumbing with too few completed runs
- logs are captured but not actually useful
- transcript review is still painful
- no meaningful comparison between runs is possible
- OpenHands prep remains vague after the harness is built

---

## Implementation guardrails

- prefer vertical slices
- no UI polish before transcript readability
- no heavy observability stack in pilot
- no generic plugin architecture in pilot
- no multi-repo support in pilot
- no external auth complexity in pilot
- no Open WebUI bridge before the native harness is useful

---

## `NOW.md` usage for this project

When this project becomes active, `NOW.md` should follow this shape:

- **Phase**
- **Current task**
- **Up next**
- **Next phase**

Keep it lean.
Push everything else to `BACKLOG.md`.

---

## Recommended first active task

**Phase 0**
Create the run contract and artifact schema, then have Codex scaffold the thin capture spine.

That means the first coding work is:
1. define the database schema
2. define artifact paths
3. define normalized event types
4. scaffold the backend
5. ingest one Codex JSONL run
6. render one transcript page

That is the first real slice.

---

## Appendix — what to defer on purpose

Defer these until the pilot proves value:

- Open WebUI integration
- mobile polish beyond basic readability
- advanced approvals UI
- multi-user support
- fancy analytics dashboards
- model auto-routing
- self-training pipelines
- generalized agent marketplace ideas
- “memory” systems unrelated to run review