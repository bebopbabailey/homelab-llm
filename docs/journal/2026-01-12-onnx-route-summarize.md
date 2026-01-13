# 2026-01-12 — ONNX Route + Summarize Pilot

## Goal / question
Test non-LLM ONNX models for routing/classification and summarization to see if
they meet speed and quality requirements for the Mini.

## Models
- Embeddings: `onnx-models/all-MiniLM-L6-v2-onnx`
- Summarization: `sshleifer/distilbart-cnn-12-6` (exported to ONNX via optimum)

## Golden sets
- Route: `docs/foundation/golden-set-route.md`
- Summarize: `docs/foundation/golden-set-summarize.md`

## Results (first pass)
### Routing (embeddings + cosine)
- 5/5 correct labels on the golden set
- Latency per request: ~2–3 ms

### Summarization (distilbart ONNX)
- Latency per request: ~0.8–1.0 s (non-stream)
- Output is generally concise and faithful; minimal hallucination seen.
- Summaries are closer to extractive than abstractive, but acceptable for MVP.

### Summarization (1500-char test)
- Added a 1500-character input to the golden set.
- Latency: ~1.5 s (non-stream)
- Output was concise and faithful (extractive summary of key points).

## Notes
- ONNX export performed on first run; cached afterward.
- This path is far faster than OpenVINO LLM summarization on this hardware.

## Next steps
- Consider adding a smaller summarizer or sentence compression model if more
  brevity is desired.
- Evaluate extraction/classification tasks using token-classification or NER ONNX models.
