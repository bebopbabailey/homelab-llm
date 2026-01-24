# OptiLLM fork + pin (durability)

## Summary
- OptiLLM is now pinned to a fork for durable local patches.
- The fork contains two patches:
  - Strip `optillm_approach` from `request_config` before forwarding upstream.
  - Fix BON rating prompt role alternation to satisfy strict chat templates.

## Repo + pin
- Fork repo: `git@github.com:bebopbabailey/optillm.git`
- Pinned commit: `7525e45`
- Pin location: `layer-gateway/optillm-proxy/pyproject.toml`

## Maintenance notes
- Update fork with upstream changes, re-apply patches, push.
- Bump the commit hash in `pyproject.toml`.
- `uv sync` to update the venv, then restart `optillm-proxy.service`.

