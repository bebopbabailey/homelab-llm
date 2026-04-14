# NOW

Active
- Move `litellm-orch` and `optillm-proxy` into live `services/` paths.
- Update runtime-lock, repo-owned unit sources, docs, and path-sensitive tests
  to the new control-plane service roots.
- Keep `vector-db` as the only remaining transitional `layer-*` service for the
  final follow-on tranche.

NEXT UP
- Land this batch, then plan and execute the final `vector-db` tranche.
