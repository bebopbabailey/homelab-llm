# Tasks: voice-gateway

## Active priorities
- Keep `voice-gateway` as the canonical LAN-visible speech facade on Orin.
- Keep Speaches localhost-only behind the facade.
- Keep the control plane docs-first and repo-canonical:
  - curated registry in `registry/tts_models.jsonl`
  - `voicectl` for scripted model lifecycle and promotion planning
  - `/ops` dashboard as an operator convenience layer over the same APIs

## Current gate
- `/ops/api/promotion/plan` must stay functional and match docs.
- Canonical docs (`SERVICE_SPEC`, `RUNBOOK`, `ARCHITECTURE`, root topology docs)
  must remain aligned with live Orin runtime truth.
- Deployment provenance manifest must remain visible from `/ops/api/state`.

## Next up
- Add deploy-script automation that writes `.deploy-manifest.json` every release.
- Add registry validation checks into pre-deploy verification.
- Expand curated registry quality notes from ongoing A/B voice evaluations.

## Explicitly out of active scope
- XTTS wrapper-proof resurrection.
- Direct Open WebUI -> Orin speech calls.
- Direct LiteLLM -> Speaches calls.
- Diarization in the default Open WebUI voice-turn path.
