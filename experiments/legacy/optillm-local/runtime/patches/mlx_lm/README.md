# MLX-LM Patch Overlay (OptiLLM Decode-Time)

This folder contains a minimal patch overlay for an experimental `mlx_lm.server` fork.

## What this patch adds
- OptiLLM-compatible request fields:
  - `optillm_approach`
  - `decoding`
  - `decoding_params` (optional object)
  - `return_decoding_metadata`
- Experimental decode-time enable flag:
  - server CLI: `--enable-optillm-decoding`
- First technique: `entropy_decoding` (non-streaming only)
- Fast path optimization when metadata is not requested (device-side entropy math)
- Optional compact response field when requested:
  - `decoding_metadata`
- Batch partitioning by decoding signature to avoid mixed-behavior batches.

## Files
- `optillm_decoding.py`: decode contract normalization + entropy processor/state.
- `server.diff`: unified diff against upstream `mlx_lm/server.py`.

## Apply manually
From a checked-out upstream `mlx-lm` repo root:

```bash
cp /path/to/homelab-llm/experiments/legacy/optillm-local/runtime/patches/mlx_lm/optillm_decoding.py mlx_lm/optillm_decoding.py
patch -p0 < /path/to/homelab-llm/experiments/legacy/optillm-local/runtime/patches/mlx_lm/server.diff
```

## Run (loopback-only example)
```bash
python -m mlx_lm.server \
  --model <your-model> \
  --host 127.0.0.1 \
  --port 8130 \
  --enable-optillm-decoding
```

## Rebase strategy
- Keep all new decode logic in `mlx_lm/optillm_decoding.py`.
- Keep `mlx_lm/server.py` edits limited to request parsing, argument plumbing, and hook insertion.
- Regenerate/refresh `server.diff` after each upstream rebase.
