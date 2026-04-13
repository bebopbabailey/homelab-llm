# Constraints: llama-cpp-server

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Inference layer: `../CONSTRAINTS.md`

## Hard constraints
- Treat this as the `llmster`-backed llama.cpp service family for GPT lanes.
- Public clients continue to use LiteLLM only.
- No live launchd/bootstrap/service mutation from this boundary without an
  explicit rollout slice and rollback.
- No new host bindings or LAN exposure beyond the approved `8126` plan.

## Allowed operations
- Documentation and contract updates.
- Template/env updates for future rollout.
- Validation command updates that remain read-only by default.

## Forbidden operations
- Pretending `fast-shadow` / `deep-shadow` are active when they are not.
- Replacing MAIN with this backend family.
- Hiding `llmster` behind vague wrapper language in repo canon.
