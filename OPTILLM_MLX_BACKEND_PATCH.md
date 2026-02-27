# Choosing a forkable server foundation for OptiLLM-style decode-time techniques on an offline MLX stack

## Executive decision

For implementing OptiLLM “N/A for proxy” decode-time / logits-loop techniques *directly* in an MLX backend (so you can keep OptiLLM as a thin gateway but still get entropy / CoT decoding / deep confidence behaviors), the best base to fork is **`mlx_lm.server` (MLX-LM’s HTTP server)**. It already owns the decoding loop end-to-end (sampler + logits processors + per-token logprob distribution + streaming), exposes the exact knobs you’ll need for inference-time control (e.g., `top_k`, `min_p`, `logit_bias`, `logprobs`, speculative decoding), and has clear, upstream-maintained extension points: a sampler is “any callable” that consumes logits, and a logits processor is “a list of callables” applied each step.

Second choice (when throughput under concurrency is the main priority) is **oMLX (`jundot/omlx`)** because it explicitly targets “continuous batching” and “paged KV cache with SSD tiering,” including cache persistence across restarts—capabilities that can materially improve tail latency and sustained batch throughput for agentic workloads. The tradeoff is complexity and distance from upstream MLX-LM internals: you’ll be grafting decode-time research hooks into a more layered serving stack.

## Feature and knob matrix

| Candidate server | Decode-loop ownership and hackability | Performance knobs exposed | API surface and schema fidelity | Batching and KV-cache features | Maintainability and upstream-breakage risk | Fit for LiteLLM ↔ OptiLLM gateway |
|---|---|---|---|---|---|---|
| **`mlx_lm.server` (MLX-LM HTTP server)** | **High.** Server code directly constructs sampler + logits processors and drives `stream_generate` / `BatchGenerator` token-by-token, with per-step access to logits (via processors) or logprob distributions (via generator output). | CLI flags include `--decode-concurrency`, `--prompt-concurrency`, `--draft-model`, `--num-draft-tokens`, `--pipeline` and default sampling knobs (`--temp`, `--top-p`, `--top-k`, `--min-p`). | Explicitly documents request fields including `top_k`, `min_p`, `logit_bias`, `logprobs`, `draft_model`, `num_draft_tokens`. Response includes logprob structures and token usage. | Implements in-process prompt/prefix caching via an LRU prompt-cache and can “trim” cached prompt state; supports batching via `BatchGenerator` with separate prefill and decode concurrency knobs. No SSD-tier KV documented. | **Best** upstream alignment: maintained in MLX-LM repo with frequent releases (latest shown Feb 2026). Warning: not recommended for production security-hardening. | **Strong.** It is already OpenAI-chat-like and supports the parameters OptiLLM’s decode-time approaches mechanically need (logprobs, sampling controls, draft model). You add one extension field and OptiLLM can pass through. |
| **`mlx-omni-server`** | **Medium–Low** for decode-loop research: it is a broader “AI suite” (chat/audio/images/embeddings) and wraps MLX-LM rather than centering on a minimal decode loop. The extension point for custom per-token logic is not documented in the server docs we could read. | Exposes standard chat knobs in docs (temperature, top_p, penalties) and supports model caching. Its docs do **not** document `top_k`, `min_p`, or `logit_bias` even though it claims “full OpenAI API compatibility.” | OpenAI-compatible endpoints with tools + streaming + structured output are documented; `response_format` JSON schema example is included. | Release notes show speculative decoding/draft-model support and logprobs-related handling (clipping), plus prompt-cache trimming support. No paged KV / SSD tiering documented. | More moving parts and more frequent “wrapper-level” changes (e.g., upgrades of MLX-LM dependency are called out in releases). | **Good** as an OpenAI/Anthropic-compatible “multi-modal local API,” but **weaker** as a foundation for decode-time research that must run inside the logits loop. |
| **oMLX (`jundot/omlx`)** | **Medium** (powerful but layered). It is built as a “production-grade inference server” with multiple subsystems (engine, scheduler, KV cache stack, admin dashboard). You can extend it, but the decode loop is less “single-file-owned.” | Explicitly configurable prefill and completion batch sizes (`--prefill-batch-size`, `--completion-batch-size`) and memory/caching controls (e.g., `--paged-ssd-cache-dir`, `--max-model-memory`). | Claims OpenAI + Anthropic API compatibility, tool calling + structured output support, and streaming tool-call buffering. | **Strongest** caching story among the three: “paged KV cache with SSD tiering,” prefix sharing and copy-on-write, and cache persistence across restarts; plus “continuous batching.” | Higher breakage risk because it composes multiple projects (notably a vLLM-on-MLX lineage) and has a larger surface area. | **Strong** when your OptiLLM use involves high concurrency (agent swarms, tool pipelines) and long contexts. But implementing custom decode-time research logic may require deeper integration work. |

**Unclear / disputed points (explicit):**  
oMLX’s README claims broad API compatibility and structured output, but the sources read here do **not** directly enumerate whether it exposes *all* decode-time knobs OptiLLM expects (e.g., exact `logprobs`/`top_logprobs` behavior, `logit_bias`, `min_p`). Those may exist via its vLLM heritage, but they are **not confirmed** by the primary README excerpt consulted.  
Similarly, `mlx-omni-server` claims “complete OpenAI API compatibility” but its OpenAI API doc emphasizes `temperature`, `top_p`, and penalties and does not list `top_k`/`min_p`/`logit_bias`.

## OptiLLM decode-time needs mapped to MLX-LM server hooks

OptiLLM explicitly labels several approaches as “N/A for proxy” (e.g., Deep Confidence, CoT Decoding, Entropy Decoding, Thinkdeeper, AutoThink), which implies they require *decode-time* control (not just request repetition / best-of-N orchestration). In addition, OptiLLM’s local inference mode calls out that it supports “logprobs” and decoding techniques like `cot_decoding` and `entropy_decoding`.

Below is the mechanical mapping to **MLX-LM server** (the recommended base):

**Access to per-step logits (or equivalent distribution)**
- MLX-LM’s generation API defines logits processors as callables that take “token history and current logits,” which is the direct “hook” you need for entropy/uncertainty computation or token-level steering.
- In the server implementation, each emitted token carries a `gen.logprobs` vector (used to extract `gen.logprobs[gen.token]` and to compute top-logprobs via argpartition), giving you per-step distribution information at decode time.

**Ability to inject logits processors / sampling hooks**
- MLX-LM explicitly supports both a pluggable sampler and an ordered list of logits processors.
- The server already constructs these (`_make_sampler`, `_make_logits_processors`) and passes them into `stream_generate` (single request) and `BatchGenerator.insert` (batched requests).

**Compute entropy / uncertainty per step**
- You can compute entropy from the per-step distribution (`gen.logprobs`) already present in the token stream, or from logits inside a logits processor for better numerical control.

**Return logprobs / top_logprobs reliably**
- The MLX-LM server documents `logprobs` support (1–10) and response fields for token logprobs, tokens, and top-logprobs.
- The server code validates `logprobs` and `top_logprobs`, collects per-token logprobs, and optionally returns top-logprobs data per position.

**Speculative decoding / draft model hooks**
- Both the server docs and CLI surface include `draft_model` and `num_draft_tokens`, and the server passes `draft_model` + `num_draft_tokens` directly into `stream_generate`.
- This means you can experiment with “drafted” branching strategies (or verification-style logic) without changing the HTTP layer first—your initial work can be decode-loop-only.

**KV/prefix caching hooks (important for multi-path decode-time techniques)**
- MLX-LM has prompt caching tools in general and the server itself maintains an in-process LRU prompt-cache, reusing cached prefixes across requests and even trimming cache entries when needed.
- This is especially relevant for decode-time techniques that explore multiple branches from a shared prefix (e.g., “k paths”)—you can avoid reprefilling the same prefix repeatedly if you structure the technique to reuse prompt caches.

## Implementation blueprint

This blueprint assumes you want OptiLLM to remain API-compatible and merely “activate” decode-time strategies via request fields (rather than rewriting OptiLLM). OptiLLM already uses extra request-body fields (e.g., an `optillm_approach` field in `extra_body`) as a control channel.

### What to fork

Fork **MLX-LM** and patch **`mlx_lm/server.py`** first, because:
- That file already parses nearly all sampling / logprobs / speculative knobs from request JSON (including `top_k`, `min_p`, `logit_bias`, `logprobs`, `draft_model`).
- It already composes sampler + logits processors and controls streaming and batching behavior.

### File-level change map

**`mlx_lm/server.py`**
- **Request schema extension**
  - Add parsing for a new field (recommended name: `decoding`, to mirror OptiLLM’s terminology for decode-time modes) and a sub-dictionary (e.g., `decoding_params`).  
  - MLX-LM currently reads fields using `self.body.get(...)` and ignores unknown keys, so adding this is low-risk for existing clients.
- **GenerationArguments extension**
  - Add a new dataclass to carry decode-time technique configuration (e.g., `DecodingArguments`) and add it into `GenerationArguments`.  
  - The server already centralizes request values into `GenerationArguments(...)` in `handle_completion`.
- **Decode-loop hook point**
  - Implement a technique-dispatch layer *inside* `_serve_single` and the batched loop:
    - `_serve_single` currently creates `sampler = _make_sampler(...)` and `logits_processors = _make_logits_processors(...)` and then iterates `for gen in stream_generate(...)`.  
    - For batching, the server inserts requests into `BatchGenerator` with per-request sampler and logits processors lists.
  - For OptiLLM-style techniques that require changing behavior mid-generation (entropy-adaptive sampling), prefer implementing a **stateful sampler** (a callable with captured mutable state) or a **logits processor** that can update shared state.
- **Logprobs and introspection outputs**
  - Keep compatibility with existing logprobs output, but optionally add extra metadata under `choices[0].logprobs` or a separate `extra` field when `decoding != None` (for example: per-step entropy, branch acceptance stats, etc.).  
  - The server already builds the final response dict in `generate_response` and conditionally includes `choices[0]["logprobs"]`.

**`mlx_lm/sample_utils.py`**
- Add one or more **new sampler constructors** that support:
  - entropy-based adaptation (needs per-step distribution; MLX-LM supports logits processors receiving logits)  
  - any additional filtering strategy you want to run purely in the sampling layer.
- You already have an established pattern: server calls `make_sampler(...)` and passes it into `stream_generate`.

**`mlx_lm/generate.py`** (only if needed)
- Only touch this if your technique needs deeper control than sampler/logits_processor allow (e.g., multi-token lookahead acceptance logic that requires coordinating across tokens or emitting multiple tokens per “step”).  
- Otherwise, keep the patch surface small and stay aligned with upstream’s deliberate hook points (sampler + processors).

### New API params and fields to add

To interoperate cleanly with OptiLLM’s “N/A for proxy” decode modes (without needing backend-specific endpoints), add the following request fields:

- `decoding`: string enum (e.g., `"entropy_decoding"`, `"cot_decoding"`, `"deepconf"`, `"thinkdeeper"`, `"autothink"`, `"none"`). The list is grounded in OptiLLM’s table of techniques.
- `decoding_params`: object. Start with parameters OptiLLM already demonstrates for entropy/CoT decoding flows (e.g., `top_k`, `min_p`, and possibly branch-count `k`), then expand as you read the specific OptiLLM technique modules.
- `return_decoding_metadata`: boolean. When true, return extra per-step diagnostics (entropy series, branch scores, etc.) for correctness/testing. Keep default false.

### Correctness and performance validation loop

- **Correctness:** Use MLX-LM’s existing `logprobs`/`top_logprobs` outputs as a “ground truth interface” to confirm your technique is acting on the distribution you think it is.  
- **Performance:** Tune and benchmark `--prompt-concurrency` and `--decode-concurrency` because MLX-LM’s server uses them to size prefill and decode batches.  
- **Spec decoding integration:** If you choose to use a draft-model in any technique (or just to accelerate baseline), validate the request/CLI integration via `draft_model` and `num_draft_tokens` which are already first-class in server docs and implementation.

## Risk register

- **Server is explicitly not production-hardened**
  - Risk: security assumptions, weaker HTTP hardening, and limited operational controls.  
  - Evidence: MLX-LM server warns it “is not recommended for production as it only implements basic security checks.”  
  - Mitigation: bind to localhost, firewall, or put a local reverse proxy in front; keep it offline per your goal.

- **Batching vs. “stateful decode-time techniques” interaction**
  - Risk: techniques that require per-request mutable state can interact badly with shared batching loops unless you design strictly per-request state containers.  
  - Evidence: server batches requests through `BatchGenerator` and injects per-request sampler/processor lists at insert time.  
  - Mitigation: ensure your sampler/logits_processor instance is per-request; avoid global mutable state.

- **Logprob format and numerical edge cases**
  - Risk: JSON encoding failures or extreme logprob values under certain sampling configurations (especially if you start returning new metrics).  
  - Evidence: `mlx-omni-server` release notes explicitly mention clipping logprobs to avoid JSON encoder errors (a known class of failure).  
  - Mitigation: clip/quantize diagnostic values; keep `return_decoding_metadata` off by default.

- **macOS memory/wired-limit behavior under very large models**
  - Risk: throughput collapse if memory is not wired correctly, paging pressure, or OS-level constraints.  
  - Evidence: MLX-LM describes wired-memory tuning via `iogpu.wired_limit_mb`, and the server sets a wired limit using device “max recommended working set size.”  
  - Mitigation: verify wired-limit behavior on your exact OS build; measure TTFT and tok/s with and without background memory pressure.

- **Upstream churn in MLX-LM internals**
  - Risk: your patch may conflict with changes in `server.py`, generation APIs, or sampling utilities over time.  
  - Evidence: MLX-LM is actively released (latest visible Feb 2026).  
  - Mitigation: keep your fork small; isolate your logic behind new “decoding” modules; upstream-friendly PRs where possible.

## Benchmark plan

To decide whether your new decode-time implementation genuinely “buys” you headroom for heavier OptiLLM batching/async workloads, benchmark at three layers: baseline server, server-under-concurrency, and technique-enabled.

**Throughput and latency**
- **Tokens/second (completion)**: measure steady-state tok/s for representative prompts and output lengths (short + long). Use both streaming and non-streaming to capture protocol overhead.  
- **TTFT (time to first token)**: especially important for agentic systems; measure TTFT under concurrency *and* with prompt cache hits/misses (because prompt caching is a major lever).  
- **Tail latency (p95/p99)**: run concurrent requests sized to your target agent-workload concurrency. For MLX-LM server, explicitly sweep `--prompt-concurrency` and `--decode-concurrency` because they shape batch sizes.

**Correctness and quality regression**
- **Logprobs sanity**: enable `logprobs`/`top_logprobs` and confirm your technique’s selection decisions correspond to the expected distribution changes.  
- **Behavioral tests**: build a small suite of prompts where entropy decoding should behave differently (high ambiguity vs low ambiguity prompts), and confirm responses change in *measurable* ways (e.g., entropy series differs, not just “vibes”).

**Memory and cache behavior**
- **Prompt cache hit rate and savings**: MLX-LM server reports cached prompt token counts in `usage.prompt_tokens_details.cached_tokens` and maintains an LRU prompt cache across requests—measure how often your workload benefits.  
- **Speculative decoding A/B**: benchmark with and without `draft_model` / `num_draft_tokens` (and tune `num_draft_tokens`) to quantify net speedups for your prompt distribution.

**Technique-enabled benchmarks**
- For each “N/A for proxy” technique you implement (grounded in OptiLLM’s list), run:
  - baseline decoding vs technique decoding at fixed output length,
  - measure TTFT, tok/s, total latency, and tail latency under concurrency,
  - and record any quality regressions or improvements.