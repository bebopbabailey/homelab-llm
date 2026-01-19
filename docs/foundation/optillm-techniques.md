# OptiLLM Techniques Cheatsheet

This is a practical guide to OptiLLM technique prefixes and when to use them.
Use these prefixes in LiteLLM env vars, e.g.:
```
OPTILLM_OPT_ROUTER_EXAMPLE_MODEL=openai/router-<base-model>
```

Local inference note (Studio):
- HF cache: `/Users/thestudio/models/hf/hub`
- Router compatibility: pin `transformers<5`

## Strategy overview (techniques vs plugins)
- Techniques (prefix-based) change how a model is queried (e.g., `moa-<base>`).
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

## moa-<base> (Mixture-of-Agents)
- Best for: hard reasoning, ambiguous prompts, multi-step planning.
- Why: runs multiple candidate answers and merges/selects the best.
- Examples:
  - “Design a scalable deployment plan for X with constraints Y.”
  - “Evaluate tradeoffs between two architectures and pick one.”

## bon-<base> (Best-of-N)
- Best for: quick quality boost with moderate latency.
- Why: samples multiple completions and picks the best.
- Examples:
  - “Draft a clean response email.”
  - “Summarize a long thread into bullet points.”

## plansearch-<base>
- Best for: structured workflows and planning-heavy tasks.
- Why: generates a plan, validates/refines it, then answers.
- Examples:
  - “Give me a step-by-step rollout plan for a new service.”
  - “Create a recording session checklist.”

## self_consistency-<base>
- Best for: correctness-sensitive reasoning.
- Why: samples multiple reasoning chains and selects the most consistent.
- Examples:
  - “Explain why A implies B with constraints.”
  - “Solve a logic puzzle or routing constraint.”

## rto-<base> (Round-Trip Optimization)
- Best for: rewrite/polish tasks.
- Why: drafts, critiques, and revises a response.
- Examples:
  - “Rewrite this transcript for clarity.”
  - “Improve documentation readability.”

## deepthink-<base> / coc-<base>
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
- OptiLLM handles use `opt-<tier>-<intent>` or `opt-<intent>-<tier>`.
- Technique prefix remains part of the OptiLLM selector (e.g., `moa-<base>`),
  so `handle` does not need to include the technique.
