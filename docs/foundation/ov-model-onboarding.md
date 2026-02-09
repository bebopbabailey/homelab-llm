# OpenVINO model onboarding (ov-*)

Status: OpenVINO is currently a standalone backend and is **not** wired as active
LiteLLM handles. This guide is kept as conditional onboarding guidance for when
OpenVINO handle wiring is explicitly re-enabled.

## Purpose
Standardize how OpenVINO GenAI models are named and exposed through LiteLLM.
The former role-based `ov-*` aliases are deprecated.

## Naming
- LiteLLM aliases are canonical model IDs: `ov-<family>-<params>-<variant>-<quant>`.
- The alias **must match** the registry key in
  `/home/christopherbailey/models/converted_models/registry.json`.
- The alias **must match** the folder name under
  `/home/christopherbailey/models/converted_models/`.

## Candidate aliases (when OpenVINO handle wiring is active)
- `ov-qwen2-5-3b-instruct-fp16`
- `ov-qwen2-5-1-5b-instruct-fp16`
- `ov-phi-4-mini-instruct-fp16`
- `ov-phi-3-5-mini-instruct-fp16`
- `ov-llama-3-2-3b-instruct-fp16`
- `ov-mistral-7b-instruct-v0-3-fp16`
- `ov-modernbert-large-encoder-fp16` (feature-extraction encoder; router POC)
- `ov-modernbert-large-router-encoder-fp16` (router checkpoint encoder; parity POC)
- `ov-modernbert-large-router-encoder-fp32` (router checkpoint encoder; parity stable)

## Where to update
- LiteLLM env: `layer-gateway/litellm-orch/config/env.local`
- LiteLLM router: `layer-gateway/litellm-orch/config/router.yaml`
- OpenVINO registry: `~/models/converted_models/registry.json`
- OpenVINO warm profiles: `platform/ops/ov-profiles/*.txt`

## Notes
- `ov-*` prompts and role aliases are archived under `docs/deprecated/`.
- Use canonical model IDs in OpenVINO and keep aliases stable.
- Before enabling any `ov-*` handles, reconcile with:
  - `docs/INTEGRATIONS.md`
  - `docs/PLATFORM_DOSSIER.md`
  - `layer-gateway/litellm-orch/config/router.yaml`
