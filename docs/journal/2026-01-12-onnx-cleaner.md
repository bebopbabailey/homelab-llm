# 2026-01-12 — ONNX Cleaner Pilot (punctuation + casing)

## Goal / question
Evaluate a non-LLM punctuation + casing model for transcript cleaning speed and fidelity.

## Model
- punctuators `pcs_en` (ONNX punctuation + casing)

## Results (golden set)
Speed is excellent (~2–3 ms per short input), but quality is uneven:
- Email/URL casing is incorrect ("Cbailey dot com", "https slash").
- Some casing oddities ("Liver", "APt") and missing apostrophes ("Lets").
- Still requires a rules layer for contacts/URLs if used in production.

## Long input (~1500 chars)
- Latency: ~0.11s
- Output quality: punctuation added but casing/formatting issues remain.

## Takeaway
Great speed, insufficient fidelity for current messaging/email use case without a
heavier rules layer or a better punctuation model.
