# ONNX Evaluation (Non-LLM Benchmarks)

Purpose: identify faster, smaller models for Benny roles that do not require full
LLM generation (routing/classification and summarization).

## Step 1 — Route/Classify + Summarize
Evaluate:
- ONNX embeddings for routing/classification (MiniLM).
- ONNX seq2seq summarization (T5-small).

Golden sets:
- `docs/foundation/golden-set-route.md`
- `docs/foundation/golden-set-summarize.md`

## Execution
Use `ops/scripts/onnx_eval.py` (creates per-role outputs and timing).

Env:
```bash
uv venv ops/.venv-onnx
uv pip install --python ops/.venv-onnx "optimum[onnxruntime]" transformers onnxruntime sentencepiece huggingface_hub numpy
ops/.venv-onnx/bin/python ops/scripts/onnx_eval.py
```

## Models (first pass)
- Embeddings: `onnx-models/all-MiniLM-L6-v2-onnx`
- Summarization: `sshleifer/distilbart-cnn-12-6` (export to ONNX at runtime)

## Cleaner pilot (punctuation + casing)
Script: `ops/scripts/clean_punct_onnx.py`
Model: `punctuators` (`pcs_en`)

Notes:
- Very fast, but casing/URL/email formatting quality is inconsistent.
- May need a stronger model or heavier rules to be viable for messaging/email.

## Notes
- These are non-LLM models; expect lower latency and deterministic outputs.
- Use non-stream tests; iOS Shortcuts calls are non-stream.
