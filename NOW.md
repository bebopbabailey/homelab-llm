# NOW

Active
- Retire the five first-party service submodules and restore plain tracked
  directories at their existing `layer-*` paths.
- Remove submodule-specific lane bootstrap, closeout, runtime-lock, and audit
  assumptions so the repo behaves like a plain monorepo.
- Keep this tranche compatibility-first: no `services/` path moves yet.

NEXT UP
- Use the flattened monorepo plus the service registry to plan the later
  `services/` and `experiments/` path migration.
