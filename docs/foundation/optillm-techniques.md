# OptiLLM Techniques Cheatsheet

This is a practical guide to OptiLLM technique values and when to use them.
Set the approach per request via `optillm_approach`, e.g.:
```json
{"model":"mlx-gpt-oss-120b-mxfp4-q4","messages":[{"role":"user","content":"ping"}],"optillm_approach":"bon"}
```

Decode-time techniques note (current direction):
- Proxy-safe orchestration stays in OptiLLM (`optillm_approach=...`).
- Decode-loop algorithms (not proxy-safe) live in MLX Omni (Studio) as `decoding=...`.
- MLX Omni accepts extra request fields (`extra = "allow"`), so we can pass `decoding` and params
  without breaking OpenAI clients.

Examples (direct to Omni via LiteLLM MLX handles):
```json
{"model":"openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct","messages":[{"role":"user","content":"ping"}],"decoding":"thinkdeeper","min_thinking_tokens":256,"stream":true}
```
```json
{"model":"openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct","messages":[{"role":"user","content":"ping"}],"decoding":"deepconf","deepconf_n":4,"stream":false}
```
```json
{"model":"openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct","messages":[{"role":"user","content":"ping"}],"logprobs":true,"top_logprobs":3,"max_tokens":16}
```

## Strategy overview (techniques vs plugins)
- Techniques (request-based) change how a model is queried (e.g., `moa`).
- Plugins (pipeline-based) add request/response transforms (e.g., `readurls`, `memory`).
- Plugins can be chained with `&` (sequential) or `|` (parallel) when supported.
- Current enabled plugins are documented in `layer-gateway/optillm-proxy/docs/FEATURES.md`.
- Default OptiLLM proxy handles for general use: _none currently registered_.

## Small-model roles (when they help)
- **Router**: classify intent and select which ensemble to call.
- **Constraint checker**: schema/format compliance before a heavy model runs.
- **Tool selector**: propose tools quickly, heavy model decides.
- **Summarizer**: compress multi-model outputs for final synthesis.

## Where small models hurt
- As full MoA peers for deep reasoning (adds noise/latency).
- In plansearch/self-consistency loops for complex tasks.

## moa (Mixture-of-Agents)
- Best for: hard reasoning, ambiguous prompts, multi-step planning.
- Why: runs multiple candidate answers and merges/selects the best.
- Examples:
  - “Design a scalable deployment plan for X with constraints Y.”
  - “Evaluate tradeoffs between two architectures and pick one.”

## bon (Best-of-N)
- Best for: quick quality boost with moderate latency.
- Why: samples multiple completions and picks the best.
- Examples:
  - “Draft a clean response email.”
  - “Summarize a long thread into bullet points.”

## plansearch
- Best for: structured workflows and planning-heavy tasks.
- Why: generates a plan, validates/refines it, then answers.
- Examples:
  - “Give me a step-by-step rollout plan for a new service.”
  - “Create a recording session checklist.”

## self_consistency
- Best for: correctness-sensitive reasoning.
- Why: samples multiple reasoning chains and selects the most consistent.
- Examples:
  - “Explain why A implies B with constraints.”
  - “Solve a logic puzzle or routing constraint.”

## rto (Round-Trip Optimization)
- Best for: rewrite/polish tasks.
- Why: drafts, critiques, and revises a response.
- Examples:
  - “Rewrite this transcript for clarity.”
  - “Improve documentation readability.”

## deepthink / coc
- Best for: deliberate, deeper reasoning.
- Why: encourages more explicit internal reasoning steps.
- Examples:
  - “Argue pros/cons for a design decision.”
  - “Diagnose a tricky system issue.”

## Technique + plugin matrix (practical defaults)
- **High quality**: `moa` or `plansearch` + optional `deepthink` + `readurls` for context.
- **Balanced**: `bon` or `self_consistency` + `router` + `memory`.
- **Fast**: `bon` or `rto` + `router` + `privacy` (if needed).
- Avoid chaining too many plugins on fast paths; each plugin adds latency.

## Ensemble tier guidance (future)
- **opt-xl (~200GB idle)**: large models only; MoA or plansearch.
- **opt-l (~150GB)**: 2 large + 1 medium; MoA or self-consistency.
- **opt-m (~100GB)**: 1 large + 1 medium + 1 small helper.
- **opt-s (~50GB)**: 1 medium + 1 small helper + optional tool router.

## Ensemble matrix (v0)
The initial evaluation matrix lives in the OptiLLM service directory:
`layer-gateway/optillm-proxy/ENSEMBLES.md`.

## Naming conventions (system-wide)
- Registry values are kebab-case only (letters, digits, dashes).
- OptiLLM handles use `opt-<tier>-<intent>` or `opt-<intent>-<tier>` when needed.
- Technique selection is per-request via `optillm_approach`, so handles do not
  need to encode the technique.
