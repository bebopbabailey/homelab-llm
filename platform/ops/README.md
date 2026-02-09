# platform/ops

Operational deployment assets for the active platform.

## Scope
- Systemd unit references and restart workflow helpers.
- Healthcheck/redeploy/restart scripts for currently managed services.
- Runtime templates (for `/etc` deployment paths).

## Canonical references
- Runtime topology/exposure: `docs/PLATFORM_DOSSIER.md`
- Integration wiring: `docs/INTEGRATIONS.md`
- Truth hierarchy: `docs/_core/SOURCES_OF_TRUTH.md`

## Notes
- This directory is operational support, not architecture canon.
- Keep script behavior aligned with active services and localhost/LAN constraints.
