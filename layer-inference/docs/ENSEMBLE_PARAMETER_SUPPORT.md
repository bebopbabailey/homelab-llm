# MLX Ensemble — Request Parameter Support (2026)

Scope: the default MLX ensemble served via `mlx-openai-server` and routed through
LiteLLM (and OptiLLM proxy when enabled). This document captures the **complete
request parameter surface** for the ensemble by referencing the official
OpenAI-compatible Chat Completions API, plus the MLX server and LiteLLM behavior
in this stack.

## Current ensemble (handles)
- `mlx-gpt-oss-120b-mxfp4-q4`
- `mlx-gemma-3-27b-it-qat-4bit`
- `mlx-gpt-oss-20b-mxfp4-q4`

These three models share the same **request parameter surface** because they are
served by the same OpenAI-compatible server and routed uniformly.

## Canonical parameter list (authoritative)
The OpenAI Chat Completions API defines the full request body schema and
parameter list. Because `mlx-openai-server` is OpenAI-compatible, this is the
canonical parameter surface for the ensemble.

Reference (authoritative list):
```
OpenAI API Reference → Chat Completions
https://platform.openai.com/docs/api-reference/chat
```

### OpenAI Chat Completions (2026) — canonical fields (non-exhaustive)
The official OpenAI reference is the source of truth; these are the core fields
commonly used for chat completions:
- Required: `model`, `messages`
- Sampling/control: `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`
- Length: `max_tokens` (deprecated), `max_completion_tokens`
- Multi-output: `n`
- Stopping: `stop`
- Streaming: `stream`
- Logits: `logit_bias`, `logprobs`, `top_logprobs`
- Tooling: `tools`, `tool_choice` (and deprecated `function_call`)
- Determinism: `seed`
- Output control: `response_format`
- Metadata/identity: `user`, `metadata`

See the OpenAI reference for the complete schema and any new fields. citeturn0search1

## Parameters supported by MLX OpenAI server (per upstream docs)
The MLX OpenAI server advertises OpenAI compatibility and supports standard
Chat Completions parameters such as:
- `model`, `messages`
- `temperature`, `top_p`
- `max_tokens`
- streaming
- function calling / tool use

It also notes compatibility with OpenAI’s request/response format.

Reference:
```
mlx-openai-server (MLX) — OpenAI-compatible API, function calling/tools
https://github.com/ml-explore/mlx-examples/tree/main/llms/llm_server
```
PyPI release notes also state OpenAI compatibility, tools, streaming, and
common OpenAI params (e.g., `temperature`, `top_p`). citeturn1search0

## LiteLLM behavior in this stack
- LiteLLM is configured with `drop_params: true`, which drops unsupported params
  rather than failing the request.
- Therefore, the **effective** parameter set is: OpenAI Chat Completions params
  minus anything the backend ignores or rejects.

Reference:
```
LiteLLM Proxy config → drop_params
https://docs.litellm.ai/docs/proxy/configuration
```
Drop-params behavior (proxy) is documented here. citeturn0search2

## OptiLLM proxy behavior (if routing enabled)
OptiLLM proxy mode accepts OpenAI-compatible requests and forwards them upstream.
Any parameter filtering happens at LiteLLM or the backend.

Reference:
```
OptiLLM proxy mode (OpenAI-compatible)
https://github.com/algorithmicsuperintelligence/optillm
```
OptiLLM advertises OpenAI-compatible proxy mode. citeturn1search5

## Practical “safe” params (validated in this stack)
The following have been validated as **accepted by the gateway** and safe to
use in normal requests:
- `model`
- `messages`
- `max_tokens`
- `temperature`
- `top_p`
- `presence_penalty`
- `frequency_penalty`

Note: acceptance means the gateway does not reject the request. Some parameters
may be ignored by the MLX backend depending on model/server version.

## Direct MLX acceptance matrix (Jan 20, 2026)
Tests were run **directly against MLX ports** (`/v1/chat/completions`) with a
minimal prompt (`"ping"`) and `max_tokens: 1`. All entries below returned HTTP
`200` (accepted).

**Accepted by each model:**
- `mlx-gpt-oss-120b-mxfp4-q4`: `temperature`, `top_p`, `presence_penalty`,
  `frequency_penalty`, `max_tokens`, `stop`, `seed`
- `mlx-gemma-3-27b-it-qat-4bit`: `temperature`, `top_p`, `presence_penalty`,
  `frequency_penalty`, `max_tokens`, `stop`, `seed`
- `mlx-gpt-oss-20b-mxfp4-q4`: `temperature`, `top_p`, `presence_penalty`,
  `frequency_penalty`, `max_tokens`, `stop`, `seed`

**Interpretation:** “Accepted” means the MLX server did not reject the request.
It does not guarantee that the backend honors every parameter (some may be
ignored depending on the model or server version).

## How to verify on demand
Run a parameter probe against LiteLLM:
```bash
curl -sS --max-time 10 http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"mlx-gpt-oss-20b-mxfp4-q4",
    "messages":[{"role":"user","content":"ping"}],
    "max_tokens":8,
    "temperature":0.2,
    "top_p":0.9,
    "presence_penalty":0.4,
    "frequency_penalty":0.2
  }'
```

## Notes
- If you need a strict list of **exactly honored** parameters per model, the
  most reliable method is to run end-to-end A/B tests or read the upstream
  `mlx-openai-server` implementation for the deployed version.
- For agent use, default to `temperature` + `max_tokens` and avoid penalties
  unless you observe measurable differences.

## Behavioral probe results (Jan 20, 2026)
Probe script: `layer-inference/docs/param_probe_mlx.py`  
Raw results: `layer-inference/docs/param_probe_results.json`

Summary (direct MLX ports):
- All three models **accepted** the tested parameters (`temperature`, `top_p`,
  `presence_penalty`, `frequency_penalty`, `max_tokens`, `stop`, `seed`,
  `max_completion_tokens`).
- `n` returned only 1 choice on all three models (likely ignored).
- `logprobs` returned no logprobs (likely ignored).
- `seed` produced deterministic output (same prompt + seed returned identical
  outputs).
- `stop` behavior was inconsistent (Gemma emitted “STOP”; GPT‑OSS did not), so
  treat `stop` as best‑effort and re‑test for your prompt patterns.

**Per-model effects (changed output detected):**
- `mlx-gpt-oss-120b-mxfp4-q4`: no observable change from `temperature/top_p/penalties`
  under this small probe (may still be honored in longer prompts).
- `mlx-gemma-3-27b-it-qat-4bit`: `temperature` and `top_p` changed output.
- `mlx-gpt-oss-20b-mxfp4-q4`: no observable change from `temperature/top_p/penalties`
  under this small probe.

**Interpretation:** these probes are intentionally small and fast. “No effect”
does not prove a parameter is ignored; it only means the short probe didn’t
surface a difference. For conclusive behavior, run longer prompts or measure
token‑level statistics.

## Extended probe (Jan 20, 2026) — parameter acceptance
Probe script: `layer-inference/docs/param_probe_mlx_extended.py`  
Raw results: `layer-inference/docs/param_probe_results_extended.json`

**Acceptance matrix (direct MLX ports):** all three models returned **HTTP 200**
for every parameter below (no validation errors):
- `temperature`, `top_p`, `top_k`, `min_p`
- `presence_penalty`, `frequency_penalty`, `repetition_penalty`
- `max_tokens`, `max_completion_tokens`
- `stop`, `seed`, `n`, `logprobs`, `top_logprobs`, `logit_bias`
- `user`, `metadata`
- `response_format` (json_object + json_schema)
- `tools` / `tool_choice`

**Behavioral observations (quick probe):**
- `n`: still returns a single choice (likely ignored by MLX server).
- `logprobs`/`top_logprobs`: no logprobs returned (likely ignored).
- `tools`/`tool_choice`: no tool calls observed (likely ignored by MLX server).
- `response_format`: responses were plain text; JSON enforcement not observed.

**Interpretation:** MLX accepts these fields but may ignore many of them.
Treat unsupported features as **best‑effort** unless you verify behavior with
longer prompts or model‑specific tests.

## Defaults matrix (recommended starting points)
Use these as **starting defaults** per task type. Tune from here.

**Transcript cleanup (strict, light correction)**  
- `temperature`: 0.3  
- `max_tokens`: 2048+  
- `top_p`: omit  
- `stop`: optional (only if you need strict termination)

**Coding / architecture**  
- `temperature`: 0.2–0.4  
- `max_tokens`: 4096–16384 (as needed)  
- `top_p`: optional (0.9 if used)

**Creative / brainstorming**  
- `temperature`: 0.7–0.9  
- `max_tokens`: 2048+  
- `top_p`: 0.9 (optional)

**Deterministic tests / evaluations**  
- `temperature`: 0.0–0.2  
- `seed`: fixed value  
- `max_tokens`: fixed

## What each parameter does (plain‑language + metaphor)
Short, practical descriptions with a quick metaphor to make intent obvious.

- `model`  
  **What it does:** selects which model handles the request.  
  **Metaphor:** choosing which chef in a kitchen will cook your meal.

- `messages`  
  **What it does:** the conversation history (system + user + assistant).  
  **Metaphor:** the full recipe card plus notes from the last cook.

- `temperature`  
  **What it does:** randomness/creativity; higher = more varied, lower = more deterministic.  
  **Metaphor:** how “adventurous” the chef is with the recipe.

- `top_p`  
  **What it does:** nucleus sampling; limits choices to the top‑probability mass.  
  **Metaphor:** only picking ingredients from the most likely bins.

- `top_k`  
  **What it does:** sampling from the top‑K most likely next tokens.  
  **Metaphor:** only looking at the top K items on the menu.

- `min_p`  
  **What it does:** floor on probability; filters out very unlikely tokens.  
  **Metaphor:** ignore anything below the “quality threshold.”

- `presence_penalty`  
  **What it does:** discourages repeating ideas already mentioned.  
  **Metaphor:** don’t re‑use ingredients you already used.

- `frequency_penalty`  
  **What it does:** discourages repeated words or phrases.  
  **Metaphor:** avoid saying the same phrase over and over.

- `repetition_penalty`  
  **What it does:** another anti‑repeat control (scales probability of repeated tokens).  
  **Metaphor:** each repeated word gets more expensive to use.

- `max_tokens`  
  **What it does:** hard cap on generated output tokens.  
  **Metaphor:** set a word limit for the response.

- `max_completion_tokens`  
  **What it does:** newer naming for output token cap (same intent as `max_tokens`).  
  **Metaphor:** another way to set the word limit.

- `stop`  
  **What it does:** tells the model to stop when it outputs any listed strings.  
  **Metaphor:** a “stop sign” in the text where the model must stop.

- `n`  
  **What it does:** number of alternative completions requested.  
  **Metaphor:** ask multiple chefs for their own version.

- `seed`  
  **What it does:** makes sampling deterministic/repeatable.  
  **Metaphor:** set the random number “dice roll” seed so you can replay it.

- `logprobs`  
  **What it does:** request token‑level probabilities in the response.  
  **Metaphor:** ask the chef to explain how confident they were about each step.

- `top_logprobs`  
  **What it does:** include top‑K alternative tokens with probabilities.  
  **Metaphor:** show the top K other ingredients the chef considered.

- `logit_bias`  
  **What it does:** push or suppress specific tokens.  
  **Metaphor:** a bouncer that discourages certain words from entering.

- `response_format`  
  **What it does:** request structured output (e.g., JSON).  
  **Metaphor:** ask the chef to plate food in a specific arrangement.

- `tools` / `tool_choice`  
  **What it does:** allow function/tool calls in the response.  
  **Metaphor:** let the chef call a helper to fetch ingredients or do a task.

- `user`  
  **What it does:** caller identifier for logging/abuse tracking.  
  **Metaphor:** the name on the order ticket.

- `metadata`  
  **What it does:** arbitrary key/value tags passed through.  
  **Metaphor:** sticky notes attached to the order.

## Cheat sheet (very short)
- **`model`**: which model to use  
- **`messages`**: what you said + system rules  
- **`temperature`**: creativity (low = strict, high = varied)  
- **`top_p`**: sampling cap (lower = safer)  
- **`max_tokens` / `max_completion_tokens`**: output length limit  
- **`stop`**: stop when a string appears  
- **`seed`**: repeatable output  
- **`presence_penalty` / `frequency_penalty`**: reduce repetition  
- **`top_k` / `min_p`**: advanced sampling filters  
- **`tools` / `tool_choice`**: allow tool calls  

## Model‑specific parameters (as of Jan 2026)
No MLX‑specific request parameters are documented beyond the **OpenAI‑compatible
Chat Completions schema**. Use the OpenAI reference for the complete request
body surface. LiteLLM will drop unsupported params when `drop_params=true`.

MLX OpenAI server documentation describes an OpenAI‑compatible API and supports
tools/function calling and streaming; it does not list model‑specific request
parameters.

### MLX server‑level knobs (not request params)
These are **server launch flags** that influence how requests are parsed or
handled, but they are not per‑request parameters:
- `--tool-call-parser` / `--reasoning-parser` (e.g., `harmony`, `qwen3`, `glm4_moe`)
- `--message-converter` for model‑specific message formatting
- `--context-length`, `--max-concurrency`, `--queue-timeout`, `--queue-size`

These settings are configured on the server (MLX launch) and apply to all
requests hitting that port.

### Model‑specific request params (documented upstream)
These are **model‑specific** controls documented by the model providers. Whether
they are honored by MLX OpenAI server depends on the server implementation.

**GPT‑OSS (120B / 20B)**  
- `reasoning_effort`: `"low" | "medium" | "high"` — documented for GPT‑OSS models.  
  This is part of the OpenAI API parameter surface for reasoning models and is
  listed in OpenAI’s API docs and the GPT‑OSS model docs. citeturn0search3turn1search0turn1search1

**Gemma 3 (27B‑IT)**  
- No provider‑documented **model‑specific request parameters** beyond the
  standard OpenAI‑style fields.
- Recommended **sampling settings** from official Gemma team guidance:
  `temperature=1.0`, `top_p=0.95`, and `top_k=64` (if supported by the backend). citeturn2search11

**Important:** MLX OpenAI server docs do **not** list `top_k` or `min_p` as
request parameters. If you need `top_k`/`min_p`, you may need an alternate
backend that exposes them (e.g., Ollama). citeturn0search7
