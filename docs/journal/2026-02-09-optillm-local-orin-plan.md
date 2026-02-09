# 2026-02-09 — OptiLLM Local on Orin (Inference Layer)

## Summary
- Added the inference-layer contract for OptiLLM local on Orin.
- Standardized Orin service root at `/opt/homelab/<service>`.
- Added deploy helper (Mini → Orin) with systemd restart + smoke test.

## Decisions
- OptiLLM local belongs to **layer-inference** (not gateway).
- Orin uses systemd; service name `optillm-local.service`.
- LAN-only exposure; access via LiteLLM routing.

## Follow-ups
- Add LiteLLM routing entry when ready to wire Orin into production.
- Add bench harness if/when needed for Orin performance.
