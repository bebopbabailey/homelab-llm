# 2026-05-11 - Gemma 4 and Qwen3.6 artifact fit

## Date
2026-05-11

## Goal / question
Refine the Gemma 4 / Qwen3.6 research around the actual model objects worth
downloading: Hugging Face repos, MLX conversions, GGUF files, low-bit quants,
mixed-precision variants, vision projector sidecars, and fine-tunes.

This supersedes the sizing emphasis in
`2026-05-10-gemma4-qwen36-artifact-fit.md` without deleting or moving that
journal entry. It is not a runtime onboarding plan. No `mlxctl`, gateway,
registry, port, or service changes were tested or proposed.

## Setup
Repo hardware context:
- Studio: Apple M3 Ultra, 256 GB unified memory, with MLX/HF and GGUF model
  stores already present.
- Mini: Intel i7-8700B, 62 GiB RAM. OpenVINO exists in repo canon, but the V2
  inventory says it is not healthy enough to count as a working baseline.
- Orin: Jetson AGX Orin Developer Kit, about 61 GiB RAM plus 30 GiB swap,
  CUDA/Linux class hardware, currently used as a speech appliance.
- HP: x86_64 Linux, about 6.7 GiB RAM; lightweight CPU-only target at best.
- Raspberry Pi-class 2 GB edge device: considered only as an extreme lower
  bound. It is not inventoried as a live repo host.

Public artifact sources checked on 2026-05-11:
- Official Qwen cards: `Qwen/Qwen3.6-35B-A3B`, `Qwen/Qwen3.6-27B`.
- Gemma 4 launch/runtime notes, including MLX and Jetson Orin Nano examples.
- MLX artifacts: Qwen3.6 35B-A3B DWQ 4-bit, Qwen3.6 27B 4-bit/OptiQ,
  Gemma 4 E2B/E4B/26B/31B 4-bit and OptiQ variants.
- GGUF artifacts: Qwen3.6 27B GGUF, Gemma 4 26B-A4B GGUF, and searched
  Gemma E2B/E4B plus Qwen3.6 35B-A3B GGUF variants.

## Findings

### Short version
Qwen3.6 is the more interesting artifact family for coding, agents, tool use,
and serious Studio experiments. Gemma 4 is the more interesting edge family,
especially E2B/E4B and especially where vision/audio inputs matter.

For this lab, do not look for one "best image" across everything. The right
split is:
- Studio MLX: Qwen3.6 27B/35B-A3B MLX first; Gemma 4 26B/31B MLX as
  multimodal comparison.
- Orin CUDA/Linux: GGUF first, especially Gemma 4 E2B/E4B and maybe Qwen3.6
  27B low quants if you want a stress test.
- Intel Mini: small GGUF or OpenVINO conversion candidates only; do not spend
  effort making 27B/35B interactive here unless the goal is a patience test.
- HP: E2B low quant or older/sub-3B models; Qwen3.6/Gemma 26B+ are not a fit.
- Raspberry Pi 2 GB: Gemma 4 E2B is still too large at normal quants. Treat
  this as sub-1B or extreme Q2 experiment territory, not a Gemma 4/Qwen3.6
  target.

### Qwen3.6 shapes
`Qwen/Qwen3.6-35B-A3B` is a 35B total / 3B activated MoE with a vision encoder,
262K native context, Apache 2.0 license, and official positioning around
agentic coding and coding stability. It is a Studio-class artifact family. The
MLX Community 4-bit DWQ conversion is listed at 20.7 GB, which is small enough
for Studio and plausibly for 24 GB Apple Silicon with limited headroom, but it
is not a Mini/HP/Raspberry Pi artifact.

`Qwen/Qwen3.6-27B` is dense, also vision-capable, and has 262K native context.
The MLX Community 4-bit conversion is listed at 16.1 GB. That makes it the best
first Qwen3.6 MLX download for this lab because it avoids MoE-specific runtime
risk while still being large enough to matter.

The most interesting MLX variant is `mlx-community/Qwen3.6-27B-OptiQ-4bit`.
It is mixed precision rather than plain uniform 4-bit: target 4.5 bits/weight,
with sensitive layers kept at 8-bit and robust layers at 4-bit. The card says
the release strips the multimodal stack by default to save memory for KV cache,
LoRA, and longer context. That is exactly the kind of optimized artifact worth
tracking for Apple Silicon if text/coding quality matters more than vision.

GGUF Qwen3.6 is viable for CUDA/Linux and CPU experiments, but the sizes push it
out of small hardware. For `bartowski/Qwen_Qwen3.6-27B-GGUF`, the card points
users at quant selection by RAM/VRAM and recommends choosing a file 1-2 GB
smaller than available GPU memory. In practice:
- Q2/IQ2 and Q3 are the only remotely plausible Mini/HP stress-test shapes.
- Q4_K_M-style files are Orin/large-RAM CPU or discrete-GPU territory, not
  2 GB edge.
- Q5/Q6/Q8 are Studio or high-VRAM CUDA artifacts.

### Gemma 4 shapes
Gemma 4 is more spread across hardware tiers. The family includes E2B, E4B,
26B-A4B MoE, and 31B dense. Hugging Face's Gemma 4 notes emphasize MLX support
through `mlx-vlm`, TurboQuant-style KV compression, and assistant/MTP
checkpoints for speculative decoding.

For Studio MLX:
- `mlx-community/gemma-4-e2b-4bit` is listed at 3.58 GB. This is the small,
  fast multimodal lane candidate.
- `mlx-community/gemma-4-e4b-it-OptiQ-4bit` is listed at 6.53 GB and uses
  mixed precision; this is the best small Gemma 4 MLX target to try before the
  larger family members.
- `mlx-community/gemma-4-26b-a4b-it-4bit` is the right larger MoE comparison
  target for Studio.
- `mlx-community/gemma-4-31b-4bit` is listed at 18.4 GB, but there is a
  credible caution from `FakeRockert543/gemma-4-31b-it-MLX-4bit`: some existing
  quantized Gemma 4 MLX builds may produce bad output if PLE layers are
  quantized incorrectly. For 31B specifically, prefer a PLE-safe artifact or
  validate output quality before trusting a benchmark.

For Orin/Linux:
- Gemma 4 E2B GGUF is the most realistic current fit. NVIDIA's Jetson Orin Nano
  Super article demonstrates Gemma 4 locally on an 8 GB Jetson-class board and
  says Q4_K_M can run after memory cleanup, with Q3 as the fallback if memory is
  tight.
- E4B GGUF may be plausible on this lab's AGX Orin because it has far more RAM
  than the Orin Nano example, but it should still be treated as an experiment
  because the repo's Orin is currently a speech host, not an LLM host.
- 26B-A4B and 31B GGUF belong to Studio or serious CUDA workstations. They may
  load on the AGX Orin's unified memory, but the likely UX is slow and not worth
  disturbing the current speech role without a separate runtime plan.

For tiny edge:
- Gemma 4 E2B is the lowest member of the family, but the observed MLX 4-bit
  artifact is 3.58 GB and common GGUF E2B Q4 files are still above the 2 GB
  class once KV cache and OS memory are included.
- A Raspberry Pi with 2 GB should be treated as outside Gemma 4/Qwen3.6 fit
  unless you are intentionally testing an extreme Q2 text-only artifact with
  tiny context and very low expectations.

## Artifact fit matrix

| Hardware | Best fit | Maybe | Avoid |
| --- | --- | --- | --- |
| Studio M3 Ultra 256 GB | Qwen3.6 27B MLX 4-bit/OptiQ; Qwen3.6 35B-A3B MLX 4-bit; Gemma 4 E4B/26B/31B MLX | GGUF Q5/Q6/Q8 for llama.cpp/LM Studio comparison | Treating any new artifact as public lane without `mlxctl` onboarding |
| iOS / Apple mobile | Gemma 4 E2B/E4B MLX-class artifacts after MLX Swift validation | Very small Qwen-family models, not Qwen3.6 27B/35B | 16 GB+ Qwen3.6/Gemma 31B artifacts |
| Orin AGX Linux/CUDA | Gemma 4 E2B/E4B GGUF; Qwen3.6 27B GGUF low/mid quants as a stress test | Qwen3.6 35B-A3B GGUF Q3/Q4 only if runtime role changes | MLX artifacts; large models while preserving speech appliance role |
| Intel Mini 62 GiB | Small GGUF; OpenVINO conversion candidates; Gemma 4 E2B/E4B CPU trials | Qwen3.6 27B Q2/Q3 GGUF as slow/offline experiment | 27B/35B as an interactive backend expectation |
| HP 6.7 GiB | Sub-3B GGUF; Gemma E2B very low quant only if nothing else is running | Q3-ish E2B experiments | Qwen3.6 27B/35B; Gemma 26B/31B |
| Raspberry Pi 2 GB | Sub-1B, Q2/IQ2 legacy/small models outside this Gemma/Qwen target | Gemma 4 E2B Q2 only as a stunt with tiny context | Normal Gemma 4 E2B Q4; all Qwen3.6 |

## Download-first shortlist
1. `mlx-community/Qwen3.6-27B-OptiQ-4bit`
   - Best first Apple Silicon artifact if the target is coding/agent quality in
     a manageable size.
   - Text-only by design in this conversion; that is a feature for memory.
2. `mlx-community/Qwen3.6-35B-A3B-4bit-DWQ`
   - Best Studio-class Qwen3.6 MoE MLX candidate.
   - Use after the 27B MLX artifact if you want to test MoE behavior.
3. `mlx-community/gemma-4-e4b-it-OptiQ-4bit`
   - Best small Gemma 4 MLX candidate: edge-ish size, mixed precision, useful
     as the fast multimodal comparison.
4. `mlx-community/gemma-4-26b-a4b-it-4bit`
   - Best large Gemma 4 Studio comparison target.
   - Especially relevant if vision/audio/multimodal behavior matters.
5. Gemma 4 E2B GGUF Q4_K_M or Q3_K_M
   - Best Orin/Pi-family Linux edge artifact to inspect.
   - For the 2 GB Raspberry Pi specifically, expect Q4 to miss and Q3/Q2 to be
     a constrained experiment rather than a usable daily model.
6. `bartowski/Qwen_Qwen3.6-27B-GGUF` low/mid quant
   - Best non-MLX Qwen3.6 path for Linux/CUDA/CPU experiments.
   - Not a small-device artifact.

## Observations / risks
- MLX is the right format for Studio and any iOS/macOS app work. GGUF is the
  right broad fallback for Linux, CUDA, CPU, and Raspberry Pi-class devices.
- Qwen3.6 27B MLX 4-bit at 16.1 GB is the cleanest serious-but-not-huge
  artifact shape. It should fit Studio trivially and medium Apple Silicon
  machines more reasonably than 35B-A3B.
- Qwen3.6 35B-A3B is attractive because only about 3B parameters activate per
  token, but the artifact is still 20 GB+ and the runtime must support the
  architecture cleanly.
- Gemma 4 31B MLX needs extra validation because PLE-safe quantization appears
  to matter. Do not assume every 31B 4-bit MLX repo is equivalent.
- Gemma 4 E2B/E4B are the only members that make sense for truly edge-oriented
  experiments. Even then, a 2 GB Raspberry Pi is below the comfortable floor.
- Fine-tunes and uncensored variants exist for both families, but they should
  not be first downloads. Start with base/instruct or optimization-focused
  quants, then evaluate fine-tunes only for a specific behavior gap.

## Next steps
1. If the next action is Apple Silicon evaluation, download
   `mlx-community/Qwen3.6-27B-OptiQ-4bit` and
   `mlx-community/gemma-4-e4b-it-OptiQ-4bit` into the Studio model store first.
2. If the next action is Orin/Linux edge evaluation, start with Gemma 4 E2B
   GGUF Q4_K_M, then Q3_K_M if memory pressure appears.
3. If the next action is Raspberry Pi 2 GB play, do not start with Gemma 4 or
   Qwen3.6. Pick a sub-1B GGUF model instead, or explicitly label Gemma 4 E2B
   Q2 as a stunt.
4. Keep any actual runtime exposure, registry row, or alias work as a separate
   approved task.

## Sources
- Qwen/Qwen3.6-35B-A3B model card:
  https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- Qwen/Qwen3.6-27B model card:
  https://huggingface.co/Qwen/Qwen3.6-27B
- MLX Qwen3.6 35B-A3B 4-bit DWQ:
  https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit-DWQ
- MLX Qwen3.6 27B 4-bit:
  https://huggingface.co/mlx-community/Qwen3.6-27B-4bit
- MLX Qwen3.6 27B OptiQ 4-bit:
  https://huggingface.co/mlx-community/Qwen3.6-27B-OptiQ-4bit
- Qwen3.6 27B GGUF:
  https://huggingface.co/bartowski/Qwen_Qwen3.6-27B-GGUF
- Gemma 4 Hugging Face launch notes:
  https://huggingface.co/blog/gemma4
- NVIDIA Gemma 4 Jetson Orin Nano Super note:
  https://huggingface.co/blog/nvidia/gemma4
- MLX Gemma 4 E2B 4-bit:
  https://huggingface.co/mlx-community/gemma-4-e2b-4bit
- MLX Gemma 4 E2B OptiQ 4-bit:
  https://huggingface.co/mlx-community/gemma-4-e2b-it-OptiQ-4bit
- MLX Gemma 4 E4B OptiQ 4-bit:
  https://huggingface.co/mlx-community/gemma-4-e4b-it-OptiQ-4bit
- MLX Gemma 4 26B-A4B 4-bit:
  https://huggingface.co/mlx-community/gemma-4-26b-a4b-it-4bit
- MLX Gemma 4 31B 4-bit:
  https://huggingface.co/mlx-community/gemma-4-31b-4bit
- PLE-safe Gemma 4 31B MLX note:
  https://huggingface.co/FakeRockert543/gemma-4-31b-it-MLX-4bit
