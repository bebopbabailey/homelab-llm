# OptiLLM Local Inference — Service Spec (Studio)

## Role
Run OptiLLM in **local inference mode** using PyTorch/Transformers on MPS (Metal).
Each instance serves one model and exposes an OpenAI-compatible API.

## Instances (v0)
- `optillm-local-high` → port **4040** → handle `opt-router-high`
- `optillm-local-balanced` → port **4041** → handle `opt-router-balanced`
- `optillm-local-fast` → port **4042** → handle `opt-router-fast`

## Runtime
- Host: Studio
- Bind: `0.0.0.0` (LAN only; LiteLLM gateway routes to it)
- Backend: PyTorch MPS (Metal)
- Precision: FP16

## Environment
- `PYTORCH_ENABLE_MPS_FALLBACK=1`
- `HF_HOME=/Users/thestudio/models/hf`
- `TRANSFORMERS_CACHE=/Users/thestudio/models/hf/hub`
- `HF_TOKEN` set for gated/large downloads

## Notes
- Use one OptiLLM process per model.
- Router approach is **disabled** on opti-local to avoid recursion.
- Pin `transformers<5` (router plugin depends on `encode_plus`).
- This service is **not** the Mini proxy; it is a separate local inference tier.
- Only **showroom** machines (Mini/Studio) receive handles. The Seagate is storage-only.

## Plugin policy
- opti-local loads only local-only approaches (no router).
- If plugins must be disabled, rename the plugin file in the venv to `*.disabled`.
