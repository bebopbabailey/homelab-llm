# CURRENT_TASK — OptiLLM Local Inference (MPS) + Default Ensemble

## Current focus (planning)
Stand up **OptiLLM local inference on the Studio** using **PyTorch/Transformers on MPS**,
while keeping OptiLLM proxy on the Mini unchanged. This enables decoding-time techniques
(entropy decoding, CoT decoding, autothink, etc.) that are not available in proxy mode.

## Goals
- Keep the **default MLX ensemble** as the primary experience.
- Add a **single OptiLLM local-inference “big guns” model** (weights-only budget ≤ 170 GB).
- Use **router** by default on the local OptiLLM instance to select techniques.
- Keep handles stable; use `opt-*` with technique in handle name if needed.

All handles must remain stable and align with `layer-gateway/registry/handles.jsonl`.

## Constraints / Naming
- Handle == registry alias; request body `model` uses the handle.
- Backend model selector must match the base model filename.
- For OpenAI-compatible upstreams, set backend model to `openai/<base-model>`.
- Handle naming: kebab-case. Prefix by category:
  - `mlx-<base-model>` for MLX models
  - `ov-<base-model>` for OpenVINO
  - `opt-<tier>-<technique>` for OptiLLM local inference (technique embedded)
  - `opt-<tier>-<intent>` for OptiLLM proxy ensembles (router/bon/moa prefixes in selector)

## OptiLLM local-inference (Studio) plan
0) Create a dedicated service directory: `layer-gateway/optillm-local` (planned).
1) Pick **one “big guns” model** (Transformers/PyTorch) under 170 GB weights-only.
2) Define service config on Studio:
   - PyTorch MPS enabled (Metal)
   - One model per OptiLLM local-inference service
3) Add LiteLLM routing to this local OptiLLM endpoint.
4) Define new `opt-*` handles whose selector uses the technique (router by default).
5) Validate via OpenWebUI and scripted prompts.

## Local OptiLLM FP16 rollout plan (phased)

### Phase 1 — Model selection + sizing (complete)
- Confirm the three FP16 models and tier mapping:
  - High: `Llama-3.1-70B-Instruct` or `Qwen2.5-72B-Instruct` (140–170 GB weights-only)
  - Balanced: `Qwen2-57B-A14B-Instruct` (90–120 GB weights-only)
  - Fast: `Qwen2.5-32B-Instruct` (50–80 GB weights-only)
- Confirm target context / max_tokens defaults (e.g., 32k).
- Decide if we start with **one** local OptiLLM service or multiple (one per tier).

### Phase 2 — Service skeleton (Studio) (complete)
- Create `layer-gateway/optillm-local` with:
  - `README.md` (purpose + MPS requirements)
  - `SERVICE_SPEC.md` (ports, env, runtime)
  - `AGENTS.md` (later)
- Add a systemd/launchd unit for the Studio local OptiLLM instance.
- Set MPS runtime flags (`PYTORCH_ENABLE_MPS_FALLBACK=1`, FP16 default).

Status update (2026-01-19):
- MLX HF cache on Studio cleared of non-target models (pending new 5-model set).
- MLX registry is empty; no MLX handles or OptiLLM proxy handles are currently registered.
- HF cache standard on Studio: `/Users/thestudio/models/hf/hub`.
- OptiLLM local launchd remains disabled until local inference setup is finalized.

### Phase 3 — Model acquisition (Studio) (in progress)
- Download FP16 weights for the selected model(s) to the Studio HF cache.
- Verify model config + tokenizer are present.
- Validate “weights-only” footprint fits target tier.
  - Current: `Qwen2.5-32B` complete, `Qwen2-57B` in progress, `Qwen2.5-72B` queued.

### Phase 4 — OptiLLM local inference wiring
- Start OptiLLM local inference with the chosen model on a Studio port.
- Validate `/v1/models` and a small prompt locally (no LiteLLM yet).
- Enable router approach by default.

### Phase 5 — Gateway integration
- Add LiteLLM routing entry + env vars for the local OptiLLM endpoint.
- Register new `opt-*` handles (technique in handle name if needed).
- Update docs: `docs/INTEGRATIONS.md`, `layer-gateway/optillm-local/*`.

### Phase 6 — Quality validation
- Run prompts from `layer-gateway/optillm-proxy/QUALITY_TEST_MATRIX.md`.
- Record notes in `docs/journal/` with latency/quality findings.

## Model candidates (local inference, PyTorch/MPS)
High (140–170 GB weights-only):
- meta-llama/Llama-3.1-70B-Instruct
- Qwen/Qwen2.5-72B-Instruct

Balanced (90–120 GB weights-only):
- Qwen/Qwen2-57B-A14B-Instruct

Fast (50–80 GB weights-only):
- Qwen/Qwen2.5-32B-Instruct

## Notes
- PyTorch MPS supports FP16; BF16 is not supported on MPS.
- Local inference enables decoding-time techniques; proxy mode does not.

## Active OptiLLM Handles (proxy)
- _None currently registered_ (pending new MLX models).

## Model Shortlist (download links)
Target MLX models (new baseline set):
- mlx-community/gpt-oss-120b-MXFP4-Q4
  Source: https://huggingface.co/mlx-community/gpt-oss-120b-MXFP4-Q4
- mlx-community/Qwen3-235B-A22B-Instruct-2507-4bit
  Source: https://huggingface.co/mlx-community/Qwen3-235B-A22B-Instruct-2507-4bit
- sjug/Mistral-Large-Instruct-2411-8bit
  Source: https://huggingface.co/sjug/Mistral-Large-Instruct-2411-8bit
- mlx-community/gemma-3-27b-it-qat-4bit
  Source: https://huggingface.co/mlx-community/gemma-3-27b-it-qat-4bit
- mlx-community/gpt-oss-20b-MXFP4-Q4
  Source: https://huggingface.co/mlx-community/gpt-oss-20b-MXFP4-Q4

## Quantization Targets
- Planning anchors: 6-bit or MXFP4 (if MLX conversion exists)
- Reasoning diversity: 8-bit or mixed 4/6 (if supported)
- Coder: 8-bit
- Fast control: 4-bit

## Phases and Subtasks

### Phase 1 — Inventory + Downloads
1. Confirm target models for each OptiLLM handle (finalize base model list).
2. Download MLX models to Studio (`~/models/hf/hub`).
3. For MXFP4 candidates:
   - If MLX model exists (e.g., gpt-oss-120b-mlx-mxfp4), download directly.
   - If only non-MLX checkpoint exists, queue for conversion.

### Phase 2 — Conversion (if needed)
1. Convert non-MLX checkpoints to MLX using `mlx_lm.convert`.
2. For MXFP4 candidates, use `--q-mode mxfp4` where supported.
3. Record resulting base model names (kebab-case, dash-only) for registry.

### Phase 3 — MLX Registry + Port Assignment
1. Register models in `/Users/thestudio/models/hf/hub/registry.json`.
2. Assign ports 8100–8102 to the primary MLX models (current boot ensemble).
3. Keep 8108–8109 free for manual testing.

### Phase 4 — LiteLLM + Handle Registry
1. Ensure `layer-gateway/registry/handles.jsonl` contains the MLX/OV handles.
2. Ensure `config/env.local` uses `openai/<base-model>` for backend model selectors.
3. Ensure `config/router.yaml` matches registry handles.

### Phase 5 — OptiLLM Wiring
1. Add OptiLLM handles for each purpose (architect, creative, coder).
2. Define OptiLLM approach per handle (moa, plansearch, self_consistency, bon, re2).
3. Validate each handle via `/v1/models` and a small prompt test.

### Phase 6 — mlxctl Enhancements
1. Add a "profile" concept to `mlxctl`:
   - `mlxctl profile load <name>`
   - `mlxctl profile unload <name>`
   - Profiles map to a port/model list.
2. Add a fast "swap" command:
   - `mlxctl swap <port> <model>` (unload + load in one command)
3. Keep changes minimal and reversible.

## Open Questions
- Where to store OptiLLM profiles (new JSON in repo vs external path)?
- Exact MLX MXFP4 artifact for Llama 3.1 405B (link needed).
- Whether to keep Qwen3-235B MXFP4 as conversion-only (non-MLX checkpoint).
