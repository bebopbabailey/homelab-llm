# OptiLLM Local Inference (Studio)

This service hosts **OptiLLM in local inference mode** on the Studio using
**PyTorch + MPS (Metal)**. It is separate from the Mini OptiLLM proxy.

## Purpose
- Enable decoding-time techniques not available in proxy mode.
- Provide a single-model OptiLLM endpoint (router selects techniques).

## Ports
- High: `4040`
- Balanced: `4041`
- Fast: `4042` (reserved)

## Handle naming (gateway)
- `opt-router-high`
- `opt-router-balanced`
- `opt-router-fast`

## Notes
- FP16 is the default precision on MPS.
- Standard HF cache on Studio: `/Users/thestudio/models/hf/hub`.
- Pin `transformers<5` for router compatibility.
- Each local OptiLLM instance serves exactly **one model**.
- The proxy on the Mini remains the primary ensemble path; this is additive.
- Only models that are **present on a showroom machine** (Mini/Studio) receive
  LiteLLM handles. The Seagate is **backroom storage** and never has handles.

## Local-only plugin policy
- opti-local must **not** load the router plugin to avoid recursion.
- opti-local should load only local-only approaches (e.g., `bon`, `moa`, `mcts`, `pvg`).

## Launch templates
- `launchd/optillm-local.plist` — local inference instance (MPS).
- `launchd/optillm-proxy-studio.plist` — proxy instance on Studio; `router_meta` is invoked per-request.
- `scripts/disable-plugins.sh` — disable router/privacy plugins in the local venv.
