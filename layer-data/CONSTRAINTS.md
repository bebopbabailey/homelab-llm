# Data Layer Constraints

## Hard constraints
- Do not introduce a new database without an approved migration plan.
- Do not store secrets or raw user data without explicit retention rules.

## Sandbox permissions
- Read: `layer-data/*`
- Write: data schemas + docs only
- Execute: no service restarts by default
- Forbidden: introducing new DBs without migration plan

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.