# OpenCode Repo Baseline

- Start from root `AGENTS.md`.
- Use `docs/_core/README.md` as the documentation hub and
  `docs/_core/SOURCES_OF_TRUTH.md` to resolve conflicts.
- Load the `repo-contract` skill before repo planning or edits.
- Load the `repo-lane-policy` skill before choosing or switching lanes.
- Treat repo-local agents and skills as the primary OpenCode control surface in
  this repo.
- Treat commands as optional entrypoints, not policy.
- For repo-analysis tasks, do not conclude until you have real repo evidence.
- If a lane cannot gather repo evidence, mark the result `UNVERIFIED` and
  recommend `repo-deep`.
- Keep `NOW.md`, verification mode, files changed, and command reporting aligned
  with root `AGENTS.md`.
