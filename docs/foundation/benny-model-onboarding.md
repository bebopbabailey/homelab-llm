# Benny Model Onboarding (OpenVINO)

Purpose: consistent, repeatable steps to add small/medium OpenVINO models for the
Mini and register them under the Benny naming scheme.

## Prereqs
- `hf` CLI installed and logged in if needed (Llama 3.2 requires license access).
- Conversion env exists: `uv venv .venv-convert` and
  `uv pip install --python .venv-convert "optimum[openvino]" sentencepiece tiktoken`.
- Source models live in `~/models`.
- Converted outputs and registry live in `~/models/converted_models`.

## Recommended Benny Names
- benny-classify-s / benny-classify-m
- benny-clean-s / benny-clean-m
- benny-tool-s / benny-tool-m
- benny-summarize-s / benny-summarize-m
- benny-extract-s / benny-extract-m
- benny-rewrite-s / benny-rewrite-m
- benny-route-s / benny-route-m

## Recommended Mapping (current)
| benny name | HF repo | weight format |
| --- | --- | --- |
| benny-route-s | Qwen/Qwen2.5-0.5B-Instruct | int8 |
| benny-route-m | Qwen/Qwen2.5-1.5B-Instruct | fp16 (shared with benny-tool-s) |
| benny-classify-s | ibm-granite/granite-3.0-2b-instruct | int8 |
| benny-classify-m | Qwen/Qwen2.5-3B-Instruct | fp16 |
| benny-clean-s | HuggingFaceTB/SmolLM2-1.7B-Instruct | int8 (active), fp16 available |
| benny-clean-m | microsoft/Phi-4-mini-instruct | int8 (active), fp16 available |
| benny-tool-s | Qwen/Qwen2.5-1.5B-Instruct | fp16 |
| benny-tool-m | Qwen/Qwen2.5-3B-Instruct | fp16 (shared with benny-classify-m) |
| benny-summarize-s | meta-llama/Llama-3.2-1B-Instruct | fp16 |
| benny-summarize-m | microsoft/Phi-3.5-mini-instruct | fp16 |
| benny-extract-s | HuggingFaceTB/SmolLM2-1.7B-Instruct | fp16 |
| benny-extract-m | microsoft/Phi-3.5-mini-instruct | fp16 (shared with benny-summarize-m) |
| benny-rewrite-s | google/gemma-2-2b-it | fp16 |
| benny-rewrite-m | meta-llama/Llama-3.2-3B-Instruct | fp16 |

Notes:
- int4 conversions exist for `benny-clean-s` and `benny-clean-m`, but GPU int4 is unstable
  on this iGPU stack (kernel compile failures). CPU-only int4 is possible but lower fidelity.
- LiteLLM currently routes `benny-clean-s` and `benny-clean-m` to `benny-clean-*-int8`.
- Pending evaluation: int8 viability for `benny-extract-*`, `benny-summarize-*`, and
  `benny-tool-*` (latency + quality vs fp16).

## Recommended Benny generation presets (Mini, OpenVINO)
Starting defaults tuned for the Mini (Intel iGPU) and OpenVINO. They favor
determinism for routing/classification, low variance for clean/extract, and
modest creativity for rewrite. LiteLLM uses `drop_params: true`, so any
unsupported parameters are ignored.

| purpose | models | temperature | top_p | top_k | repetition_penalty | max_tokens |
| --- | --- | --- | --- | --- | --- | --- |
| route/classify | benny-route-*, benny-classify-* | 0.01 | 1 | 1 | 1.0 | 128 |
| clean (s) | benny-clean-s | 0.01 | 1 | 1 | 1.05 | 512 |
| clean (m) | benny-clean-m | 0.01 | 1 | 1 | 1.05 | 512 |
| extract (s) | benny-extract-s | 0.01 | 1 | 1 | 1.05 | 1024 |
| extract (m) | benny-extract-m | 0.01 | 1 | 1 | 1.05 | 2048 |
| tool use | benny-tool-* | 0.1 | 0.9 | 40 | 1.05 | 512 |
| summarize (s) | benny-summarize-s | 0.2 | 0.9 | 40 | 1.1 | 512 |
| summarize (m) | benny-summarize-m | 0.2 | 0.9 | 40 | 1.1 | 1024 |
| rewrite | benny-rewrite-* | 0.5 | 0.9 | 50 | 1.05 | 1024 |

## Download (examples)
Use `hf download` to place repos under `~/models/<RepoName>`:

```bash
hf download Qwen/Qwen2.5-1.5B-Instruct --local-dir ~/models/Qwen2.5-1.5B-Instruct
hf download Qwen/Qwen2.5-3B-Instruct --local-dir ~/models/Qwen2.5-3B-Instruct
hf download HuggingFaceTB/SmolLM2-1.7B-Instruct --local-dir ~/models/SmolLM2-1.7B-Instruct
hf download microsoft/Phi-3.5-mini-instruct --local-dir ~/models/Phi-3.5-mini-instruct
hf download meta-llama/Llama-3.2-1B-Instruct --local-dir ~/models/Llama-3.2-1B-Instruct
hf download meta-llama/Llama-3.2-3B-Instruct --local-dir ~/models/Llama-3.2-3B-Instruct
hf download Qwen/Qwen2.5-0.5B-Instruct --local-dir ~/models/Qwen2.5-0.5B-Instruct
hf download ibm-granite/granite-3.0-2b-instruct --local-dir ~/models/granite-3.0-2b-instruct
hf download google/gemma-2-2b-it --local-dir ~/models/gemma-2-2b-it
```

If a model is gated, run:
```bash
hf auth login
```

## Convert + Register
Run the converter from the repo:

```bash
cd ~/homelab-llm/services/ov-llm-server
./scripts/ov-convert-model
```

If you have it on PATH:
```bash
ov-convert-model
```

Optional flags:
```bash
./scripts/ov-convert-model --weight-format int8
./scripts/ov-convert-model --task text-generation-with-past
```

Download + convert in one step:
```bash
ov-convert-model --model Qwen/Qwen2.5-1.5B-Instruct --weight-format int8
```

## Phi Compatibility Patch (automatic)
Phi-3.5 and Phi-4 models require two small compatibility symbols that are not
present in released Transformers. The converter now runs
`services/ov-llm-server/scripts/patch-transformers-compat.sh` automatically.
If you rebuild `.venv-convert`, this patch will re-apply on the next conversion.

When prompted for a custom name, enter the Benny name (e.g. `benny-tool-s`).
The converter writes:
- OpenVINO IR to `~/models/converted_models/<name>/task-text-generation-with-past__wf-<format>`
- `conversion.json` in that folder
- Registry entry in `~/models/converted_models/registry.json`

## Offload Originals to HP
The converter offloads originals to the HP by default and removes local copies.
If offload fails, it falls back to keeping the copy under `~/models/og_models`.

Defaults:
- Host: `hp`
- Destination: `/root/models/og_models`

Override if needed:
```bash
export OV_MODEL_OG_REMOTE=hp
export OV_MODEL_OG_REMOTE_DIR=/root/models/og_models
```

## Quick Verify
```bash
jq '.models | keys' ~/models/converted_models/registry.json
```

## LiteLLM Wiring
Once converted, add the Benny entries to LiteLLM:
- Router: `services/litellm-orch/config/router.yaml`
- Env vars: `services/litellm-orch/config/env.local` (copy from `env.example`)

Each `BENNY_*_MODEL` should be `openai/<benny-name>` and all `BENNY_*_API_BASE`
should point to `http://127.0.0.1:9000/v1`.

Lean note: some Benny aliases intentionally point to the same OpenVINO model
name to avoid duplicate backends. See `services/litellm-orch/config/env.local`
for the current alias mapping.

## Prompt templates (LiteLLM prompt manager)
- Prompt files live under `docs/prompts/benny/*.prompt.md`.
- Each file maps to a LiteLLM prompt ID with the same name (e.g., `benny-clean-m`).
- Prompts are stored in the LiteLLM DB (`LiteLLM_PromptTable`); new edits should
  be re-imported to bump the version.
- Prompt index (latest versions): `docs/prompts/benny/index.json`.
- Sync script: `ops/scripts/sync-benny-prompts` (updates index only).
- LiteLLM injects these prompts automatically per model via
  `services/litellm-orch/config/prompt_injector.py` and
  `services/litellm-orch/config/router.yaml` callbacks, so clients do **not**
  need to pass `prompt_id`.

## Notes
- Conversion always uses `--trust-remote-code` (required by some model families).
- Keep names stable; the registry key is the model name LiteLLM will reference.
- OpenVINO currently errors if `temperature` is exactly `0` while sampling is enabled,
  so router defaults use `0.01` for deterministic-ish tasks.
- Golden test set for cleaning: `docs/foundation/golden-set-cleaning.md`.
