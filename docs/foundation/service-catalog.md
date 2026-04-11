# Service Catalog

`platform/registry/services.jsonl` is now the canonical machine-readable
service taxonomy for the repo.

Compatibility-first posture:
- current filesystem paths still use `layer-*`
- `planned_path` records the destination service-centric layout
- `maturity` distinguishes supported services from experiments and historical
  placeholders
- `parent_service_id` allows explicit child-service relationships such as
  `mcp-tools/web-fetch`

Useful commands:
```bash
uv run python scripts/service_registry.py list --json
uv run python scripts/service_registry.py show litellm-orch --json
uv run python scripts/service_registry.py path open-webui
uv run python scripts/service_registry_audit.py --strict --json
```

Registry conventions:
- `path` is the current live repo path during migration
- `planned_path` is the intended destination under `services/` or
  `experiments/`
- `legacy_paths` remains empty until a path move actually happens
