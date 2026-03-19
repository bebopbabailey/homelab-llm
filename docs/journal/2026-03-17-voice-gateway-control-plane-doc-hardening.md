# 2026-03-17 — Voice Gateway control-plane doc hardening

## Summary
- Reconciled voice-gateway service docs, layer docs, and root canonical docs to
  the live Orin speech-appliance reality.
- Hardened the repo-first control-plane contract:
  - curated TTS registry (`registry/tts_models.jsonl`)
  - `voicectl` CLI
  - `/ops` dashboard/API
  - deploy provenance manifest surfaced in `/ops/api/state`

## Runtime evidence (Orin)
- `systemctl cat voice-gateway.service` shows active service on Orin checkout:
  - `WorkingDirectory=/home/christopherbailey/voice-gateway-canary`
  - `ExecStart=.../.venv/bin/voice-gateway-service --host 192.168.1.93 --port 18080`
- `curl -fsS http://192.168.1.93:18080/health/readiness | jq .`
- `curl -fsS http://192.168.1.93:18080/ops >/dev/null`
- `curl -fsS http://192.168.1.93:18080/ops/api/state -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq .`
- Deploy provenance manifest present at:
  - `/home/christopherbailey/voice-gateway-canary/.deploy-manifest.json`

## Contract outcomes
- Canonical Orin host docs now describe voice-gateway as live and validated.
- Service docs now explicitly separate:
  - gateway runtime env
  - control-plane env
  - legacy XTTS-local CLI env (non-canonical serving path)
- Historical XTTS wrapper-proof tasks/demo guidance removed from active
  operator path in favor of current service contract checks.
