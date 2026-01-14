# 2026-01-13 — OpenVINO strengths plan + device mode evaluation

## Current Reality (Mini)
- Runtime env: `/etc/homelab-llm/ov-server.env` has `OV_DEVICE=GPU`.
- LiteLLM routes `benny-clean-s`/`benny-clean-m` to int8 models.
- int4 exists in the registry but is GPU-unstable on this iGPU stack.

## Decision Direction
- Enable **CPU+GPU** usage for multi-request throughput using `AUTO` or `MULTI:GPU,CPU`.
- Validate whether `AUTO`/`MULTI` improves **single-request latency** for 1500-char cleaning.
- Treat this Mini as an always-on edge box: likely strengths are **STT, vision, async throughput** more than big LLM reasoning.

## Planned Tests (LLM)
- Compare `OV_DEVICE=GPU` vs `AUTO` vs `MULTI:GPU,CPU` for `benny-clean-s` and `benny-clean-m`.
- Measure:
  - Single-request latency (1500-char prompt)
  - Concurrent throughput (2–4 parallel requests)
  - Any stability regressions

## Hypotheses (to validate)
- `AUTO`/`MULTI` improves throughput, not single-request latency.
- `benny-clean-s` will remain the viable low-latency option for iOS shortcuts.
- LLM cleaning at 1500 chars may be too slow for this host vs specialized STT/vision models.

## Next (Non-LLM Strengths)
- Identify minimal viable services on this box:
  - STT (OpenVINO-optimized ASR or ONNX)
  - Vision (object detection / action recognition)
  - TTS (if latency acceptable)
- Create small, repeatable benchmarks for each category and record results here.
