# optillm-local (Architecture)

## Objective
Provide a forkable, rebase-friendly MLX-LM foundation for OptiLLM decode-time
techniques that require logits-loop ownership.

## Design (experimental)
1. Upstream base
- Clone `ml-explore/mlx-lm` at a pinned commit.

2. Minimal patch surface
- Keep new logic in `mlx_lm/optillm_decoding.py` (overlay module).
- Keep `mlx_lm/server.py` modifications minimal and additive.

3. Request contract
- Technique selectors:
  - `decoding`
  - `optillm_approach` (compatibility alias/path)
- Optional metadata output:
  - `return_decoding_metadata`

4. First implemented technique
- `entropy_decoding`:
  - per-step entropy from logits distribution
  - adaptive temperature modulation
  - optional compact metadata summary in final response

5. Isolation model
- Dedicated loopback port for experimental server (example `127.0.0.1:8130`).
- No production service rewiring in this stage.

## Concurrency model
- Decode-time settings are normalized into a per-request signature.
- Batches are partitioned by signature to avoid mixed decode behavior.
- State is request-local; no global mutable decode state.
