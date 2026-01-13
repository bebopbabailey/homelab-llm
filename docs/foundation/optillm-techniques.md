# OptiLLM Techniques Cheatsheet

This is a practical guide to OptiLLM technique prefixes and when to use them.
Use these prefixes in LiteLLM env vars, e.g.:
```
OPTILLM_JERRY_XL_MODEL=openai/moa-jerry-xl
```

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
