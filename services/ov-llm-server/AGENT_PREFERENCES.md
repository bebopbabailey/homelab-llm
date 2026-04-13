# Agent Preferences

## Workflow
- Update `TASKS.md` and `AGENTS.md` before implementing new features.
- During debugging, avoid updating `TASKS.md` unless explicitly requested; log fixes in chat and update later.
- Prefer small, reversible increments; ask before large refactors.
- Keep docs current; avoid backlog drift.
- Confirm proposed changes against the latest project documentation as of today (current session date).

## Constraints
- List non-negotiables early (stack, tools, services not to touch).
- Do not change global/system settings unless requested.

## Code & Structure
- Favor simple, deterministic naming and file layout.
- Put evolving details in metadata or config, not filenames.
- Prefer minimal automation over heavy tooling unless needed.

## Testing & Verification
- State test expectations explicitly, even if no tests exist.
- When unsure, ask before adding new test frameworks.

## Configuration
- Keep a single source of truth (env vars + one registry file).
- Avoid duplicate or conflicting configuration sources.
