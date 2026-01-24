# Personas (LiteLLM → OptiLLM)

Goal: keep iOS Shortcuts minimal. Clients send only `model` and `messages`. The
persona alias expands server‑side into:
- base model (small/medium/large)
- persona system prompt
- default sampling params
- OptiLLM approach (`extra_body.optillm_approach`)

## How it works
- LiteLLM exposes persona aliases as `model` values (e.g., `char-transcript`).
- A LiteLLM pre‑call hook rewrites the request:
  - sets `optillm_base_model` to the chosen base model (keeps `model` as the preset alias)
  - prepends persona system prompt to `messages`
  - injects default params when not provided by the client
  - adds `extra_body.optillm_approach` when applicable
- A LiteLLM post‑call hook augments `p-opt-max`:
  - fans out to extra approaches (leap + plansearch)
  - reduces deterministically (single reducer call)
  - runs a final re2 cleanup
  - implemented as a guardrail: `config/promptopt_guardrail.py`
  - reducer runs directly against the MLX OpenAI server (no OptiLLM approach)

Implementation: `config/persona_router.py` via LiteLLM `callbacks`.

## Persona aliases
- `char-transcript` → medium (mlx‑qwen3‑next‑80b‑mxfp4‑a3b‑instruct)
- `p-transcript` → medium (same as char-transcript)
- `p-transcript-md` → medium (Markdown allowed if it helps readability)
- `char-casual` → large
- `char-duck` → medium
- `char-careful` → large
- `char-brainstorm` → large
- `char-jsonclerk` → medium
- `p-opt-fast` → large (prompt optimizer, fast)
- `p-opt-balanced` → large (prompt optimizer, balanced)
- `p-opt-max` → large (prompt optimizer, max compute)

## Preset aliases (p-*)
All p-* presets default to the large model.
- `p-fast` → re2&bon (fast, concise)
- `p-safe` → leap&re2&bon (cautious, low-hallucination)
- `p-deep` → leap&re2&bon&moa (maximum reasoning)
- `p-chat` → leap&re2 (wise, conversational)
- `p-fast-super` → re2&bon&moa (fast + extra compute)
- `p-safe-super` → leap&re2&bon&moa (safe + extra compute)
- `p-deep-super` → leap&re2&bon&moa (deep + extra compute)
- `p-plan` → leap&re2 (structured planning)
- `p-care` → re2 (precision / caution)
- `p-seek` → re2&bon (exploration)
- `p-make` → re2&bon (execution)
- `p-spark` → bon (creative output)
- `p-plan-max` → leap&re2&bon&moa (max compute)
- `p-care-max` → leap&re2&bon&moa (max compute)
- `p-seek-max` → bon&moa (max compute)
- `p-make-max` → re2&bon&moa (max compute)
- `p-spark-max` → bon&moa (max compute)
- `p-opt-fast` → re2 (prompt optimizer, fast)
- `p-opt-balanced` → plansearch&re2 (prompt optimizer, balanced)
- `p-opt-max` → re2 + fan-out (leap/plansearch) + reducer + re2 cleanup (max compute)

## Model size override
Clients can override size using `metadata.size`:
- `metadata.size=small|medium|large`

Or pin a specific base model:
- `metadata.base_model=mlx-gpt-oss-20b-mxfp4-q4` (or other known base model)

## Transcript preprocessing
For `char-transcript`, `p-transcript`, and `p-transcript-md`, the pre‑call hook strips punctuation
outside words (apostrophes inside words are preserved) before the system prompt
is applied. This keeps clients lightweight while matching the transcript spec.

Transcript personas (locked):
- Expressiveness: vivid, not dramatic (neutral written tone)
- Pacing: varied/balanced sentence length
- Emphasis: commas/periods default; em‑dashes/semicolons/ellipses allowed sparingly for readability only
- Exclamations: rare
- Word correction: moderate (only when intent is clearly implied)
- Output: cleaned transcript only (no metadata, no summaries)

## Curl tests (one per persona)
```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"char-transcript","messages":[{"role":"user","content":"i was uh walking down the street"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"p-transcript","messages":[{"role":"user","content":"i was uh walking down the street"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"char-casual","messages":[{"role":"user","content":"hey what\'s up?"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"char-duck","messages":[{"role":"user","content":"my build is failing on CI"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"char-careful","messages":[{"role":"user","content":"summarize risks of running a local LLM"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"char-brainstorm","messages":[{"role":"user","content":"ideas for a homelab dashboard"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"p-opt-fast","messages":[{"role":"user","content":"rewrite: clean transcripts"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"p-opt-max","messages":[{"role":"user","content":"rewrite: clean transcripts"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"char-jsonclerk","messages":[{"role":"user","content":"return JSON with ok=true"}]}'
```

## Rollback
- Remove the `char-*` entries from `config/router.yaml`.
- Remove `persona_router.persona_router_instance` from `litellm_settings.callbacks`.
- Restart `litellm-orch.service`.

---

## Consistency checklist (what presets do and do not guarantee)
Use this before relying on a preset for reproducible outputs.

**What presets make consistent (most of the time):**
- System prompt (intent framing) is fixed per preset.
- Sampling defaults (temperature/top_p/max_tokens) are fixed per preset.
- OptiLLM chain/approach is fixed per preset.
- Base model selection is fixed per preset unless explicitly overridden.

**What presets do NOT guarantee:**
- Deterministic output (LLMs are still stochastic unless a seed is supported).
- Identical results across different context history lengths.
- Identical results when tools or external data change.
- Identical results across model version or quantization changes.

**If you need higher consistency:**
- Use lower temperature + tighter top_p/top_k.
- Keep prompts short and stable (avoid large, mutable history).
- Avoid tool calls unless you need fresh data.
- Use a dedicated “strict” preset with conservative params.
