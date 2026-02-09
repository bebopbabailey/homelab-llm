# AGENTS — optillm-local (Orin)

## Role & Scope
You maintain **this service only**. It is an inference backend on Orin.

## Non‑Negotiables
- **Inference only** (no routing / gateway logic).
- **Ports:** keep on `4040` unless a migration plan exists.
- **Dependencies:** use `uv` only; no global `pip`.
- **CUDA required**; do not install drivers or OS packages in this repo.
- **No secrets in repo**.

## Start Here
- `SERVICE_SPEC.md`
- `RUNBOOK.md`
- `README.md`
- `systemd/optillm-local.service`

## Expected Behavior
- OpenAI‑compatible endpoints under `/v1`.
- Auth required (`OPTILLM_API_KEY`).

## Tests
- `curl -fsS http://127.0.0.1:4040/v1/models -H "Authorization: Bearer $OPTILLM_API_KEY" | jq .`

## Definition of Done
- Service runs under systemd on Orin.
- `/v1/models` responds.
- Docs updated for any behavior change.
