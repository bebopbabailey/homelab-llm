# 2026-01-12 — OpenVINO Cleaning Performance + Fidelity

## Goal / question
Determine how fast and accurate OpenVINO cleaning models are on the Mini,
and whether int8/int4 quantization improves latency without harming quality.

## Hardware / software
- Host: Mac mini (Intel Core i7-8700B, 6C/12T, 64GB RAM)
- iGPU: Intel UHD Graphics 630 (CoffeeLake-H GT2)
- OS: Ubuntu 24.04.3 LTS, kernel 6.8.0-90-generic
- OpenVINO: 2025.4.1
- openvino_genai: 2025.4.1
- Intel OpenCL runtime: 23.43.027642

## Models
- benny-clean-s: HuggingFaceTB/SmolLM2-1.7B-Instruct
- benny-clean-m: microsoft/Phi-4-mini-instruct

Quantizations tested:
- fp16 (baseline)
- int8 (OpenVINO weight compression)
- int4 (OpenVINO weight compression)

## Golden set
`docs/archive/2026-02-golden-set-cleaning.md` (5 transcripts).

## Key results
### 1500-character (non-stream) latency
Via LiteLLM (OpenVINO backend, int8):
- clean-s int8: ~54s
- clean-m int8: ~134s

Direct OpenVINO baseline (fp16, GPU):
- clean-s fp16: ~45s
- clean-m fp16: ~319s

### Multi-device
OV_DEVICE=AUTO did not improve single-request latency vs GPU-only.

### int4 stability
int4 **crashes on GPU**:
```
intel_sub_group_block_read ... Program build failed
```
int4 only ran on CPU for testing.

### Golden set qualitative comparison (CPU)
Int4 often introduced semantic drift or rephrasing for clean-s.
Int8 was generally more stable, though still occasionally "over-corrects."

Examples:
- clean-s int4 sometimes reorders meaning (bad for cleaning).
- clean-m int4 sometimes damages URLs.

## Observations / risks
- GPU int4 is not viable on this iGPU stack (kernel compile failure).
- clean-m remains slow even with int8 on GPU.
- clean-s is the most viable local option.
- Additional speed likely requires smaller models or offloading to MLX.

## Next steps
- Keep clean-s int8 as default for iOS shortcuts.
- Consider dropping clean-m or routing long transcripts to MLX (jerry-clean-l).
- Evaluate smaller model families or non-OpenVINO backends (IPEX-LLM / MLX).
