# 2026-02-onnx-evaluation (Archived)

Status: archived. This evaluation plan is OpenVINO/ONNX-centric and is no longer
an active direction.

Purpose: identify faster, smaller models for OpenVINO roles that do not require full
LLM generation (routing/classification, summarization, cleaning, and extraction).

## Step 1 — Route/Classify + Summarize
Evaluate:
- ONNX embeddings for routing/classification (MiniLM).
- ONNX seq2seq summarization (T5-small).

Golden sets (archived with this plan):
- `docs/archive/2026-02-golden-set-route.md`
- `docs/archive/2026-02-golden-set-summarize.md`

## Execution
Use `platform/ops/scripts/onnx_eval.py` (creates per-role outputs and timing).

Env:
```bash
uv venv platform/ops/.venv-onnx
uv pip install --python platform/ops/.venv-onnx "optimum[onnxruntime]" transformers onnxruntime sentencepiece huggingface_hub numpy
platform/ops/.venv-onnx/bin/python platform/ops/scripts/onnx_eval.py
```

## Models (first pass)
- Embeddings: `onnx-models/all-MiniLM-L6-v2-onnx`
- Summarization: `sshleifer/distilbart-cnn-12-6` (export to ONNX at runtime)

## Next candidates (non-LLM)
- Cleaning/extraction: fast punctuation/casing + rule pass (ONNX + rules).
- Keyword/entity extraction: lightweight NER or token classification (ONNX).

## Cleaner pilot (punctuation + casing)
Script: `platform/ops/scripts/clean_punct_onnx.py`
Model: `punctuators` (`pcs_en`)

Notes:
- Very fast, but casing/URL/email formatting quality is inconsistent.
- May need a stronger model or heavier rules to be viable for messaging/email.

## Notes
- These are non-LLM models; expect lower latency and deterministic outputs.
- Use non-stream tests; iOS Shortcuts calls are non-stream.
