# Personas (LiteLLM → OptiLLM)

Goal: keep iOS Shortcuts minimal. Clients send only `model` and `messages`. The
persona alias expands server‑side into:
- base model (small/medium/large)
- persona system prompt
- default sampling params
- OptiLLM approach (`extra_body.optillm_approach`) when applicable

## How it works
- LiteLLM exposes persona aliases as `model` values (e.g., `char-transcribe`).
- A LiteLLM pre‑call hook rewrites the request:
  - sets `optillm_base_model` to the chosen base model (keeps `model` as the preset alias)
  - prepends persona system prompt to `messages`
  - injects default params when not provided by the client
  - adds `extra_body.optillm_approach` when applicable
- `p-opt-*` use Best‑of‑N (`bon`) with explicit `n` values per preset.
  - Guardrail fan‑out/reducer is disabled by default but remains available in
    `config/promptopt_guardrail.py` if needed later.

Implementation: `config/persona_router.py` via LiteLLM `callbacks`.

## Persona aliases
- `char-transcribe` → large (mlx‑gpt‑oss‑120b‑mxfp4‑q4)
- `p-transcribe` → large (strict verbatim + baseline punctuation)
- `p-transcribe-vivid` → large (strict verbatim + minimal Markdown emphasis)
- `p-transcribe-clarify` → large (light rewrite for clarity)
- `p-transcribe-md` → large (strict verbatim + minimal Markdown emphasis)
- `char-casual` → large
- `char-duck` → medium
- `char-careful` → large
- `char-brainstorm` → large
- `char-jsonclerk` → medium
- `p-opt-fast` → small (prompt optimizer, fast)
- `p-opt-balanced` → medium (prompt optimizer, balanced)
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
- `p-plan-max` → heavy‑small/light‑large guardrail (20B plansearch&re2 → 120B re2)
- `p-care-max` → leap&re2&bon&moa (max compute)
- `p-seek-max` → heavy‑small/light‑large guardrail (20B plansearch&re2 → 120B re2)
- `p-make-max` → re2&bon&moa (max compute)
- `p-spark-max` → bon&moa (max compute)
- `p-opt-fast` → bon&re2, `n=3`, `max_tokens=600`
- `p-opt-balanced` → bon&re2, `n=4`, `max_tokens=1200`
- `p-opt-max` → re2 + guardrail triad fan‑out (see below), `max_tokens=800`

### p-opt-max triad fan‑out (guardrail)
`p-opt-max` uses an explicit fan‑out reducer (single pass) with three upstream
models, then a deterministic reducer on the 80B model, and optional cleanup:
- 20B: `bon&re2`, `n=4–6` (dynamic)
- 80B: `bon&re2`, `n=1–2` (dynamic)
- 120B: `plansearch&re2`, `n=1`
- Reducer: 80B, temp 0, output only the chosen prompt
- Cleanup: optional `re2` if output drifts
  - Guardrail logs `cleanup_triggered` and `cleanup_reason` for future tuning.

## Model size override
Clients can override size using `metadata.size`:
- `metadata.size=small|medium|large`

Or pin a specific base model:
- `metadata.base_model=mlx-gpt-oss-20b-mxfp4-q4` (or other known base model)

## Transcript preprocessing
For `char-transcribe`, `p-transcribe`, and `p-transcribe-vivid`, the pre‑call hook strips punctuation
outside words. Apostrophes and hyphens inside words are preserved before the system prompt
is applied. This keeps clients lightweight while matching the transcript spec.

Transcript personas (locked):
- Expressiveness: vivid and character‑forward (not theatrical)
- Pacing: prefer multi‑clause sentences with natural pauses; avoid choppy splits
- Emphasis: commas/periods default; em‑dashes/semicolons/ellipses encouraged when they improve rhythm or emphasis
- Exclamations: rare
- Word correction: **none** (wording is preserved; only disfluencies may be removed)
- Output: cleaned transcript only (no metadata, no summaries)
- Reasoning content is stripped from transcript responses (guardrail).

Transcript variants:
- `p-transcribe-clarify`: light rewrite for clarity, preserve meaning
- `p-transcribe-vivid`: expressive cadence + minimal Markdown emphasis
- `p-transcribe-md`: minimal Markdown emphasis for readability

## Known‑good transcript baseline (must not drift)
Default `p-transcribe` settings:
- temperature: **0.0**
- top_p: **1.0**
- presence_penalty: **0.0**
- frequency_penalty: **0.0**
- max_tokens: **2400**
- **No OptiLLM approach** (single‑pass)

Preprocess (server‑side):
- Strip punctuation outside words
- Preserve apostrophes/hyphens inside words
- Normalize em/en dashes to `-` before the model

Output:
- Cleaned transcript text only
- No labels/headings/markdown wrappers
- Must start immediately with transcript content

Tests:
- `python -m unittest discover -s layer-gateway/litellm-orch/tests -p \"test_transcribe_*.py\"`

Debug:
- `TRANSCRIBE_DEBUG=1` logs request payload metadata for transcribe presets.
- `TRANSCRIBE_DEBUG_FULL=1` additionally logs full messages (use with care).

## Curl tests (one per persona)
```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"char-transcribe","messages":[{"role":"user","content":"i was uh walking down the street"}]}'

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"p-transcribe","messages":[{"role":"user","content":"i was uh walking down the street"}]}'

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
