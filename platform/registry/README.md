# Platform Registries

These files are the canonical machine-readable taxonomy and registry surfaces
for the repo.

Current registries:
- `services.jsonl` — service identity, path, maturity, relationships, and historical legacy paths
- `handles.jsonl` — LiteLLM/public handle registry
- `models.jsonl` — model registry data used by the control plane
- `lexicon.jsonl` — deterministic terminology correction data

Rules:
- prefer registry data over prose summaries when they disagree
- use `services.jsonl` for service taxonomy, not `layer-*` paths
- treat `legacy_paths` as historical traceability only
- do not use `legacy_paths` for runtime resolution or operator fallback

Useful commands:
```bash
uv run python scripts/service_registry.py list --json
uv run python scripts/service_registry.py show litellm-orch --json
uv run python scripts/service_registry_audit.py --strict --json
uv run python scripts/validate_handles.py
```
