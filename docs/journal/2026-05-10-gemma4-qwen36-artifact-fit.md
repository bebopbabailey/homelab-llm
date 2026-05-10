# Gemma 4 / Qwen3.6 Artifact Fit Survey

## Objective
Pick practical downloadable artifact shapes for Gemma 4 and Qwen3.6 without
starting runtimes, changing ports, or downloading models. This is an artifact
survey only: Hugging Face repos, formats, quant families, file sizes, tuned
variants, and host fit.

## Sources checked
- Official Gemma 4 cards: `google/gemma-4-E2B-it`,
  `google/gemma-4-E4B-it`, `google/gemma-4-26B-A4B-it`,
  `google/gemma-4-31B-it`.
- Official Qwen cards: `Qwen/Qwen3.6-35B-A3B`,
  `Qwen/Qwen3.6-35B-A3B-FP8`, `Qwen/Qwen3.6-27B`.
- MLX conversions: `mlx-community/gemma-4-e2b-it-4bit`,
  `mlx-community/gemma-4-e4b-it-4bit`,
  `mlx-community/gemma-4-26b-a4b-it-4bit`,
  `mlx-community/gemma-4-31b-it-4bit`,
  `mlx-community/Qwen3.6-35B-A3B-4bit`,
  `unsloth/Qwen3.6-27B-UD-MLX-4bit`.
- GGUF repos: `unsloth/gemma-4-E2B-it-GGUF`,
  `unsloth/gemma-4-E4B-it-GGUF`,
  `unsloth/gemma-4-26B-A4B-it-GGUF`,
  `unsloth/gemma-4-31B-it-GGUF`,
  `unsloth/Qwen3.6-35B-A3B-GGUF`,
  `unsloth/Qwen3.6-27B-GGUF`.
- Repo hardware context: `docs/PLATFORM_DOSSIER.md`,
  `docs/foundation/topology.md`, `docs/foundation/mlx-registry.md`,
  `docs/foundation/orin-agx.md`, `docs/foundation/ov-llm-server.md`.

## Model families
- Gemma 4 has four main sizes: E2B, E4B, 26B-A4B MoE, and 31B dense. The
  E2B/E4B cards position the small models for mobile and edge deployments;
  26B-A4B is sparse with about 25.2B total and 3.8B active parameters; 31B is
  the dense quality-first shape.
- Qwen3.6 has a 35B-A3B MoE shape with 35B total and 3B active parameters,
  plus a 27B dense shape. The 35B-A3B official repos include BF16/safetensors
  and FP8/safetensors; community repos provide MLX and GGUF quants.

## Format rule
| Format | Best target here | Why |
| --- | --- | --- |
| MLX safetensors | Studio, possibly iOS/MLX Swift only after library support is confirmed | Native Apple path; best fit for Studio unified memory. |
| GGUF | Orin CUDA/Linux, Mini CPU/Ollama experiments, HP-class Linux, Raspberry Pi experiments | Portable llama.cpp path with many quant sizes. |
| BF16/FP8 safetensors | CUDA servers or conversion source | Useful as source or high-end runtime input; not a first download for constrained hosts. |
| mmproj GGUF sidecars | Multimodal GGUF runs | Add roughly 0.9-2.3 GB depending model; skip for text-only probes. |

## Download-first list
| Rank | Artifact | Size cue | First target | Reason |
| --- | --- | ---: | --- | --- |
| 1 | `mlx-community/Qwen3.6-35B-A3B-4bit` | 20.4 GB repo | Studio MLX | Best Qwen3.6 local quality/fit candidate for Studio-class memory. |
| 2 | `mlx-community/gemma-4-26b-a4b-it-4bit` | 15.6 GB repo | Studio MLX | Strong sparse Gemma 4 option with smaller artifact than dense 31B. |
| 3 | `mlx-community/gemma-4-31b-it-4bit` | 18.4 GB repo | Studio MLX | Dense Gemma quality lane; heavier than 26B-A4B but still Studio-feasible. |
| 4 | `mlx-community/gemma-4-e2b-it-4bit` | 3.6 GB repo | Studio small lane, iOS experiments | Smallest Gemma 4 MLX target; best first on-device candidate. |
| 5 | `mlx-community/gemma-4-e4b-it-4bit` | 5.2 GB repo | Studio small lane, Mini RAM, iOS tablet-class experiments | Better small-model quality than E2B with still modest artifact size. |
| 6 | `unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ3/UD-IQ4` | 13.2-22.4 GB file | Orin/Mini/HP Linux experiments | Portable Qwen MoE path when MLX is unavailable. |
| 7 | `unsloth/Qwen3.6-27B-GGUF:IQ3/IQ4` | 12.0-17.6 GB file | Orin/Mini/HP Linux with enough RAM | Dense Qwen shape; likely slower/heavier than 35B-A3B MoE for same host. |
| 8 | `unsloth/gemma-4-E2B-it-GGUF:UD-IQ2/Q3/Q4` | 2.3-3.2 GB file | Pi 4GB/8GB, HP light Linux, Mini CPU | Small portable Gemma; 2GB Pi remains marginal because file size is not full runtime memory. |

## Fit matrix
| Host class | Best artifact shape | Practical candidates | Avoid first |
| --- | --- | --- | --- |
| Studio MLX | MLX 4-bit | Qwen3.6 35B-A3B 4-bit, Gemma 4 26B-A4B 4-bit, Gemma 4 31B 4-bit, Gemma E2B/E4B 4-bit | GGUF unless comparing llama.cpp, BF16/FP8 unless converting or testing high-memory paths. |
| Orin CUDA/Linux | GGUF low/medium quant or CUDA-native safetensors only with a separate runtime plan | Gemma E2B/E4B GGUF first; Qwen3.6 35B-A3B UD-IQ3/UD-IQ4 only if memory headroom and llama.cpp CUDA support are confirmed | MLX artifacts; large BF16 downloads. |
| Intel Mini | GGUF small CPU path, OpenVINO conversion experiments | Gemma E2B/E4B GGUF, possibly Qwen3.6 35B-A3B very low-bit as a RAM-fit experiment | Treating 26B+/31B+/35B as ergonomic interactive CPU targets. |
| iOS / MLX Swift | Small MLX only | Gemma 4 E2B/E4B MLX after confirming `gemma4` support in the app/library; tiny Qwen family alternatives if needed | Qwen3.6 27B/35B and Gemma 26B/31B phone targets. |
| HP-class light Linux | GGUF CPU/iGPU | Gemma E2B/E4B Q3/Q4; Qwen3.6 27B/35B only as low-bit batch/offline experiments | BF16 and heavy multimodal sidecars. |
| Raspberry Pi 2GB | Smaller-than-this-survey or extreme low-bit only | Sub-1B/1B-ish models outside Gemma 4/Qwen3.6; Gemma E2B UD-IQ2 is still about 2.3 GB before KV/runtime overhead | Gemma E2B Q4 and all Qwen3.6/Gemma 26B+ artifacts. |

## Memory ladder
| Memory tier | Artifact shape that can be worth testing |
| ---: | --- |
| ~2 GB | Do not start with Gemma 4 or Qwen3.6. Use sub-1B/1B-ish GGUF or cloud/off-host. |
| 4-8 GB | Gemma 4 E2B/E4B GGUF low quants; MLX E2B/E4B only on Apple targets with enough unified memory. |
| 16 GB | Gemma E2B/E4B comfortably; Gemma 26B-A4B or Qwen3.6 35B-A3B only at very low GGUF quants with limited context. |
| 24 GB | Qwen3.6 35B-A3B UD-IQ3/UD-IQ4 GGUF or MLX 4-bit; Gemma 26B-A4B MLX/GGUF Q4. |
| 32 GB | Qwen3.6 35B-A3B Q4, Gemma 31B Q4, Qwen3.6 27B Q4 with useful context headroom. |
| 64 GB | Higher GGUF quants, FP8 experiments, longer context; avoid BF16 unless the runtime and cache budget are deliberate. |
| 256 GB | Broad comparison tier: MLX 4/6/8-bit, GGUF Q6/Q8, FP8/BF16 conversion source, and multimodal sidecars. |

## Artifact size cues
| Family | MLX 4-bit | GGUF useful low/mid files |
| --- | ---: | --- |
| Gemma 4 E2B IT | 3.6 GB | UD-IQ2 2.3 GB; Q3/Q4 about 2.4-3.2 GB; mmproj adds about 1.0 GB for vision. |
| Gemma 4 E4B IT | 5.2 GB | UD-IQ2 3.5 GB; Q3/Q4 about 3.9-5.1 GB; mmproj adds about 1.0 GB. |
| Gemma 4 26B-A4B IT | 15.6 GB | UD-IQ2 about 10.0 GB; IQ4 about 13.6 GB; Q4_K about 16.5-17.0 GB; mmproj adds about 1.2 GB. |
| Gemma 4 31B IT | 18.4 GB | UD-IQ2_XXS 8.5 GB; Q3 about 13.2-15.4 GB; Q4 about 16.4-18.8 GB; mmproj adds about 1.2 GB. |
| Qwen3.6 35B-A3B | 20.4 GB | UD-IQ2 about 10.8-12.3 GB; Q3 about 13.2-16.8 GB; Q4 about 17.7-22.4 GB; mmproj adds about 0.9 GB. |
| Qwen3.6 27B | 26.2 GB community MLX 4-bit | UD-IQ2 about 9.4-11.8 GB; Q3 about 12.0-14.5 GB; Q4 about 15.4-17.6 GB; mmproj adds about 0.9 GB. |

## Tuned and community variants
- Prefer official base/instruct and `mlx-community`/`unsloth` conversion repos
  before fine-tunes. They are easier to compare, explain, and replace.
- Community Qwen3.6 variants with MTP preserved, uncensored/heretic tuning,
  Claude/Kimi reasoning distillation, and NVFP4/GPTQ experiments are worth a
  separate quality survey only after a base artifact fits.
- For multimodal work, record whether the text model file and `mmproj` sidecar
  were both downloaded; the sidecar can change the memory/disk result enough to
  invalidate a text-only fit estimate.

## Decision
For this repo, the first no-runtime download candidates should be:

1. Studio: `mlx-community/Qwen3.6-35B-A3B-4bit`,
   `mlx-community/gemma-4-26b-a4b-it-4bit`,
   `mlx-community/gemma-4-31b-it-4bit`.
2. Small Apple/on-device: `mlx-community/gemma-4-e2b-it-4bit` and
   `mlx-community/gemma-4-e4b-it-4bit`, with MLX Swift support confirmed before
   treating iOS as viable.
3. Non-Apple Linux: Gemma 4 E2B/E4B GGUF first; Qwen3.6 35B-A3B GGUF low-bit
   only after checking disk, RAM, and target llama.cpp support.
4. Raspberry Pi 2GB: do not spend the first download on these families.

No models were downloaded. No runtime, port, registry, gateway, or service
changes were made.
