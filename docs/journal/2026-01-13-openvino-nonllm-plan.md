# 2026-01-13 — OpenVINO + non-LLM plan (tie up loose ends)

## Goals
- Confirm which OpenVINO LLM roles are viable at int8 on the Mini.
- Decide where int4 makes sense (CPU-only vs GPU via IPEX-LLM).
- Identify non-LLM models that can replace or augment LLM roles.
- Define next test plan for STT/TTS/Vision.

## LLM follow-up (OpenVINO)
- Evaluate int8 for `benny-extract-*`, `benny-summarize-*`, `benny-tool-*`.
- Compare latency + quality vs fp16.
- Keep current default routing until evaluation is complete.

## int4 decision
- int4 on GPU is unstable on this iGPU stack (kernel compile failures).
- CPU-only int4 is possible but lower fidelity.
- Determine if IPEX-LLM unlocks stable GPU int4 and whether the tradeoffs are worth it.

## Non-LLM replacements
- Routing/classification: ONNX embeddings (MiniLM) — fast and accurate.
- Summarization: ONNX distilbart — acceptable speed/quality for short inputs.
- Cleaning/extraction: punct/case ONNX + rule pass; consider token-classification/NER.

## Next: STT/TTS/Vision plan
- STT: OpenVINO/ONNX ASR models (latency/RTF focus).
- TTS: lightweight local TTS candidates (latency focus).
- Vision: object detection/action recognition via OpenVINO/ONNX.
- Define minimal benchmarks and record results in journal.
