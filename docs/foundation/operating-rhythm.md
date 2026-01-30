# Operating Rhythm (Agent-Compatible)

This is the working style for this repo. Agents should mirror this cadence.

## Stage Loop (repeat per layer/service)
1) **Inventory** — map current reality (services, ports, models, ownership).
2) **Constraints** — define boundaries, naming, ownership rules.
3) **Minimal contract** — smallest viable registry/doc/handle.
4) **Wire** — implement and connect the pieces.
5) **Validate** — quick smoke tests and real usage checks.
6) **Codify** — update docs and journal; capture decisions.
7) **Prune** — remove clutter, trim scope, tighten the loop.

## Operating Principles
- One source of truth per concept (avoid duplication).
- Keep tasks short; prefer small, repeated loops.
- Measure before optimizing; keep baselines.
- Document only what changed; avoid stale plans.
- Put long outputs, large diffs, or copy/paste blocks in `SCRATCH_PAD.md` for review.
- For any ops actions, state host + service + safe validation first.
- `NOW.md` must reflect the active task; update it when the active work changes.
- `NOW.md` contains only active work + a single “NEXT UP” section. Everything else goes to `BACKLOG.md`.

---

## Agent Modes (Human‑Body Metaphor)
Use this to guide preset behavior and agent stance.

### Discover (Sensor: eyes + ears)
- Behaviors: ask clarifying questions, list unknowns, gather context, avoid early commitment.
- One‑off task example: “Summarize the current topology and identify missing info.”

### Design (Planner: brain + cortex)
- Behaviors: propose 2–3 options, analyze tradeoffs, pick a path, state assumptions.
- One‑off task example: “Propose three routing strategies for LiteLLM + OptiLLM with pros/cons.”

### Build (Executor: hands + muscles)
- Behaviors: implement directly, keep output concise, minimize detours.
- One‑off task example: “Add a new preset alias and update the router config.”

### Verify (Auditor: balance + reflexes)
- Behaviors: check for errors, edge cases, regressions, and list fixes.
- One‑off task example: “Run a smoke test of p‑deep and report latency + token usage.”
