# Gemma 4 / Qwen3.6 Landscape Survey

## Objective
Supersede `2026-05-10-gemma4-qwen36-artifact-fit.md`. The earlier note is a
blob-size inventory. This note asks the useful question: what are Gemma 4 and
Qwen3.6 good for, where are their runtime ecosystems strongest, which hardware
classes make sense in a greenfield setup, and which custom/community variants
look worth attention?

This is still a no-download, no-runtime survey. Treat local hosts as possible
hardware, not as binding topology. Any current service, OS, port, or gateway
can change in a future plan.

## Source posture
Confidence levels:
- Strong: official model cards/docs and runtime docs.
- Medium: Hugging Face repo metadata, model trees, conversions, and provider
  recipes observed on 2026-05-10.
- Low: community reports and benchmark posts unless independently reproduced.

Primary sources checked:
- Gemma 4 official cards:
  <https://huggingface.co/google/gemma-4-E2B-it>,
  <https://huggingface.co/google/gemma-4-E4B-it>,
  <https://huggingface.co/google/gemma-4-26B-A4B-it>,
  <https://huggingface.co/google/gemma-4-31B-it>
- Qwen3.6 official cards:
  <https://huggingface.co/Qwen/Qwen3.6-35B-A3B>,
  <https://huggingface.co/Qwen/Qwen3.6-27B>,
  <https://huggingface.co/Qwen/Qwen3.6-35B-A3B-FP8>
- Ecosystem/runtime docs:
  <https://github.com/huggingface/blog/blob/main/gemma4.md>,
  <https://qwen.readthedocs.io/en/v3.0/deployment/sglang.html>,
  <https://build.nvidia.com/spark/llama-cpp/overview>
- Community/anecdotal signal:
  Hugging Face model trees and search results for MLX/GGUF/fine-tune variants,
  plus Reddit/local-AI reports about Gemma 4 MLX/GGUF behavior, Qwen3.6 GGUF
  quants, CUDA 13.2 issues, and tool-call parser rough edges.

## Family read
| Family | Best mental model | Strongest uses | Watch-outs |
| --- | --- | --- | --- |
| Gemma 4 E2B/E4B | Small multimodal edge models with thinking mode | Mobile/laptop assistants, OCR/captioning, audio snippets, local utility, light coding help | Smaller models are attractive because they run everywhere, not because they beat Qwen on agentic coding. |
| Gemma 4 26B-A4B | Efficient MoE multimodal workstation model | Balanced research, image/document reasoning, coding assistance, autonomous-agent experiments | MoE fit depends heavily on runtime quality; not all MLX/GGUF paths behave equally yet. |
| Gemma 4 31B | Dense flagship Gemma shape | Highest Gemma reasoning/coding/vision quality, long-document work, stable dense behavior | Heavier active compute than the 26B-A4B MoE; less edge-friendly. |
| Qwen3.6 35B-A3B | Agentic coding MoE with only 3B active params | Coding agents, repository reasoning, tool use, long-context workflows, cheap high-throughput local serving | Needs correct reasoning/tool parsers and chat templates; MoE/kernel/runtime details matter a lot. |
| Qwen3.6 27B | Dense agentic coding model | Stronger predictable dense behavior for coding/reasoning when memory is available | More active compute than 35B-A3B; less compelling for tiny edge devices. |

Observed HF metadata on 2026-05-10: Gemma 4 official cards show very high
30-day downloads across all sizes, especially 31B and 26B-A4B. Qwen3.6
35B-A3B has a large model tree with dozens of adapters/fine-tunes and hundreds
of quantizations, which is the strongest signal that the community is actively
porting it into local runtimes.

## Capabilities that matter
Agents and coding:
- Qwen3.6 is the more purpose-built coding-agent family. The official 35B-A3B
  card explicitly emphasizes agentic coding, repository-level reasoning,
  historical thinking preservation, Qwen-Agent, Qwen Code, tool-call parsing,
  MTP, and OpenAI-compatible serving recipes for vLLM and SGLang.
- Qwen3.6 27B is the dense option when the priority is predictable quality over
  sparse efficiency. It is attractive on 24-48 GB GPUs, large Apple unified
  memory, and multi-GPU servers.
- Gemma 4 has native function-calling support and improved coding, but its
  center of gravity is broader: multimodal reasoning, local assistants,
  document/image understanding, and controllable thinking mode.
- For real coding agents, parser/template support is not optional. Qwen wants
  `qwen3` reasoning parsers and `qwen3_coder` tool parsers in vLLM/SGLang.
  Gemma tool calling can work through modern runtimes, but community reports
  show tool behavior can differ between Ollama, llama.cpp, Continue, and MLX.

Research and long context:
- Both families are long-context families, but they use it differently.
  Gemma small models are 128K-class and medium models are 256K-class. Qwen3.6
  advertises 262K native context, with extension paths on the 35B-A3B card.
- Qwen3.6 is better framed as long-context agent/repo work: read a large code
  base, preserve reasoning, iterate with tools.
- Gemma 4 is better framed as long-context multimodal research: documents,
  screenshots, charts, images, video frames, and multilingual synthesis.
- For either family, full context is a hardware product decision. A model that
  "fits" at Q4 may still fail the use case once KV cache, vision tokens, and
  output budget are included.

Multimodal:
- Gemma 4 is the more coherent multimodal family. Official cards describe all
  models as text+image to text, with E2B/E4B also supporting audio input.
  Gemma cards document variable image token budgets, video-as-frames, and audio
  prompts for ASR/translation on small models.
- Qwen3.6 is also image-text-to-text on the official cards. Its multimodal
  story is useful, but the family is being marketed and adopted more around
  coding agents and long-context tool use.
- For OCR/document parsing, Gemma 31B and 26B-A4B are the stronger first
  Gemma candidates; E4B is the small practical edge candidate.

Edge/mobile:
- Gemma E2B/E4B are the first serious mobile/edge candidates in this survey.
  They are small enough to make MLX, Core ML-style experiments, WebGPU, Rust,
  llama.cpp, and mobile app integrations plausible.
- Qwen3.6 35B-A3B is surprisingly usable on smaller GPUs in community GGUF
  reports because only 3B parameters are active per token, but it is not a
  phone/Pi model. Treat it as a workstation/server model that can be squeezed,
  not as an edge-native model.
- Raspberry Pi 2GB remains outside the practical target zone for these
  families. Use it as a client, controller, gateway, or test harness unless the
  experiment is deliberately about extreme low-bit novelty.

## Runtime and ecosystem landscape
| Ecosystem | Gemma 4 posture | Qwen3.6 posture | Best hardware fit |
| --- | --- | --- | --- |
| Transformers | Official first-party path; supports multimodal processors and thinking parse helpers | Official path; compatible with vLLM/SGLang/KTransformers according to card | Linux CUDA, large Apple via PyTorch/MPS experiments, workstation dev |
| vLLM | Official HF deploy widgets show Gemma serving; stronger for CUDA servers than small devices | First-class official recipes for max context, parser setup, tool use, MTP, text-only memory saving | NVIDIA multi-GPU, high-VRAM single GPU for lower context |
| SGLang | Official deploy widgets show Gemma serving | Official docs recommend recent SGLang and document reasoning/tool parsing | NVIDIA multi-GPU and agent-serving experiments |
| llama.cpp / GGUF | Strong Gemma support, including image+text in the HF Gemma ecosystem post | Active Qwen3.6 GGUF support and conversions; community reports mention CUDA/tooling rough edges | Mac/Windows/Linux local apps, NVIDIA CUDA, Apple Metal, CPU fallback |
| Ollama / LM Studio / Jan | Good consumer-local path, usually via GGUF and runtime-managed templates | Good for quick local Qwen trials if model/template support is current | Developer laptops, desktops, quick comparison |
| MLX | Many Gemma and Qwen conversions exist | Many conversions exist, especially Qwen3.6 35B-A3B 4-bit and 8-bit | Apple Silicon with enough unified memory |
| MLX Swift / iOS | Gemma E2B/E4B are the likely targets, but app/library support must be tested | Qwen3.6 is generally too large for phone-class use | iPhone/iPad/Mac app experiments |
| OpenVINO | Possible conversion/evaluation path, but not the center of these releases | Possible conversion/evaluation path, not the obvious first ecosystem | Intel Mini/NUC CPU/iGPU experiments |
| WebGPU / browser | HF Gemma ecosystem explicitly calls out transformers.js/browser directions | Less central for Qwen3.6 sizes | Demos, educational tools, small Gemma only |

Greenfield hardware affinity:
- Best coding-agent workstation: NVIDIA 24-48 GB GPU or multi-GPU Linux,
  running Qwen3.6 via vLLM/SGLang first, llama.cpp GGUF second.
- Best Apple local lab: Mac Studio with high unified memory, testing both
  MLX and llama.cpp/Metal. Do not assume MLX is automatically best for Gemma 4;
  community reports currently favor GGUF/llama.cpp for some Gemma 4 behavior.
- Best multimodal local research box: high-memory NVIDIA or Apple unified
  memory with Gemma 4 31B/26B-A4B and Qwen3.6 35B-A3B side by side.
- Best edge/mobile path: Gemma E4B first, E2B if latency/battery wins. Use
  Qwen3.6 from edge devices as a remote endpoint, not on-device.
- Best Pi/HP-light path: use these as clients, routers, or automation hosts.
  If local inference is required, step down to smaller families outside this
  survey.

## Community and customization landscape
Gemma 4:
- Conversion coverage is broad: official HF, GGUF, MLX, WebGPU/browser notes,
  Rust mentions, Ollama/LM Studio-style local app paths.
- Fine-tune landscape is thinner than Qwen's coding-agent culture so far. The
  visible community variants are mostly assistant conversions, heretic/
  uncensored variants, APEX/GGUF alternatives, and quantization repacks.
- The most interesting Gemma custom direction is not another chat fine-tune;
  it is multimodal specialization: OCR, document parsing, mobile assistant UX,
  audio snippets on E2B/E4B, visual inspection, and local private research.

Qwen3.6:
- Conversion and tuning activity is much denser. HF model trees and searches
  show many quantizations plus MLX, GGUF, MTP-preserved, NVFP4/GPTQ, reasoning
  distill, uncensored/heretic, and Claude/Opus-style variants.
- The community appears to be using Qwen3.6 for local coding agents, web-agent
  experiments, OpenAI-compatible local serving, and squeezing MoE models onto
  smaller GPUs with llama.cpp CPU-MoE/offload tricks.
- The useful customizations to track are MTP-preserved variants, robust GGUF
  quant families, tool-parser-compatible templates, and coding-agent fine-tunes.
  The noisy customizations are novelty uncensor merges unless a specific task
  needs refusal reduction.

Community risk signals to verify locally before trusting:
- CUDA 13.2 low-bit GGUF instability reports around llama.cpp/Qwen3.6; prefer
  known-good CUDA/toolchain versions when testing.
- Qwen tool calling can fail from parser/template mismatch even when raw text
  quality is good.
- Gemma 4 MLX behavior may lag GGUF/llama.cpp in some app stacks; test both on
  Apple rather than assuming MLX wins.
- Multimodal GGUF runs require the correct `mmproj` sidecar; Qwen3.6 and
  Gemma sidecars are not interchangeable.

## Recommended greenfield experiments
1. Coding agents: start with Qwen3.6 35B-A3B on vLLM or SGLang using official
   reasoning and tool-call parser settings. Compare against Qwen3.6 27B dense
   only if enough memory exists and tool reliability matters more than sparse
   efficiency.
2. Local agent apps through llama.cpp: test Qwen3.6 35B-A3B GGUF and Gemma 4
   26B-A4B GGUF behind `llama-server` OpenAI-compatible endpoints. Evaluate
   tool calls, file-edit workflows, context retention, and prompt-template
   behavior before judging model quality.
3. Multimodal research: test Gemma 4 31B and 26B-A4B first for screenshots,
   charts, scanned documents, OCR, and long visual/document prompts. Add Qwen3.6
   35B-A3B when the task mixes image reasoning with agentic code/tool work.
4. Mobile/edge: test Gemma 4 E4B, then E2B, across MLX/MLX Swift, llama.cpp,
   Ollama/LM Studio, and browser/WebGPU demos. Measure latency, battery,
   memory pressure, and whether audio/image inputs are actually exposed by the
   app stack.
5. Fine-tune watchlist: for Qwen3.6, track MTP-preserved and coding-agent
   variants. For Gemma 4, track multimodal/OCR/document variants. Do not start
   with uncensored merges unless the task explicitly needs that behavior.

## Bottom line
If the goal is agents and coding tools, Qwen3.6 is the lead family. Start with
35B-A3B for sparse efficiency and 27B when dense predictability is worth the
memory.

If the goal is broad local AI utility, multimodal research, mobile/edge, or
private document/image/audio workflows, Gemma 4 is the more interesting family.
Start with E4B for edge/mobile, 26B-A4B for balanced workstation use, and 31B
when quality matters more than efficiency.

The main mistake to avoid is treating model choice as a file-size problem. The
real decision is model family plus runtime parser/template support plus hardware
memory/KV budget plus client workflow. Those four things decide whether a model
is useful.

No models were downloaded. No runtime, service, gateway, registry, port, or
host changes were made.
