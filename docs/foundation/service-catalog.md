# Service Catalog

`platform/registry/services.jsonl` is now the canonical machine-readable
service taxonomy for the repo.

Current posture:
- active service roots live under `services/` or `experiments/`
- `maturity` distinguishes supported services from experiments and historical
  placeholders
- localhost-only experimental backends may also live under `experiments/` when
  they sit behind LiteLLM and are not part of the public client contract
- `parent_service_id` allows explicit child-service relationships such as
  `mcp-tools/web-fetch`
- `layer-*` is taxonomy/navigation only and is not a live service-root surface

Useful commands:
```bash
uv run python scripts/service_registry.py list --json
uv run python scripts/service_registry.py show litellm-orch --json
uv run python scripts/service_registry.py path open-webui
uv run python scripts/service_registry_audit.py --strict --json
```

Registry conventions:
- `path` is the current live repo path
- `planned_path` should match `path` in the steady state
- `legacy_paths` records historical service locations for traceability only
- `legacy_paths` must not be used for runtime resolution or operator fallback
