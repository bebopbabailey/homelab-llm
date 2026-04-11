# NOW

Active
- Remove repo-local runtime/tooling dependence on raw `layer-*` paths where the
  service registry is now the canonical source of truth.
- Tighten runtime-lock validation around `service_refs` and object path refs so
  later `services/` / `experiments/` moves do not require another lock-format shim.
- Keep this tranche compatibility-first: no directory moves yet.

NEXT UP
- Move low-risk services and experiments into `services/` and `experiments/`
  once repo-local tooling resolves service paths through the registry cleanly.
