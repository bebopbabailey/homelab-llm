# 2026-03-19 — Shadow ports retired and docs hardened

## Summary
- Retired the Studio shadow rollout ports `8123-8125`.
- Quarantined the active `com.bebop.mlx-shadow.8123` launchd job through the
  Studio scheduling policy instead of keeping it as dormant recovery
  infrastructure.
- Kept the settled public stack unchanged:
  - `main` on MLX `8101`
  - `fast` and `deep` on shared `llmster` `8126`
- Kept `optillm-proxy` on `4020`, but codified it as non-core operator
  infrastructure rather than part of the canonical `main` / `fast` / `deep`
  lane surface.

## Runtime change
- `8123` was running on Studio even though it was no longer part of the active
  gateway alias surface.
- The Studio scheduling policy was updated so:
  - `com.bebop.mlx-shadow.8123`
  - `com.bebop.mlx-shadow.8124`
  - `com.bebop.mlx-shadow.8125`
  are retired labels, not managed active inference labels.
- The old repo template for `com.bebop.mlx-shadow.8123` was deleted.

## Documentation change
- Cleaned active source-of-truth and operational docs so they no longer present
  `8123-8125` as approved rollout or dormant recovery space.
- Preserved historical journal records as the source history for the old shadow
  experiments.
- Clarified that `4020` remains deployed but is operator/opt-in infrastructure,
  not part of the canonical public alias stack.

## Locked reality after closeout
- Public LiteLLM aliases remain:
  - `main`
  - `fast`
  - `deep`
- Active Studio app listeners for the settled stack are:
  - `8101`
  - `8126`
  - `4020` as non-core operator path
- Retired Studio shadow ports:
  - `8123`
  - `8124`
  - `8125`
