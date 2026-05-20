# 2026-05-19 - Qwen3.6 MLX coding specialist slice

## Objective
Implement the first agentic ensemble backend slice around
`mlx-community/Qwen3.6-27B-OptiQ-4bit` as a coding specialist, gated by direct
Studio backend evidence before any LiteLLM shadow alias or OpenHands exposure.

## Result
Stopped before LiteLLM and OpenHands. The artifact is downloaded and staged on
Studio, and `mlxctl` was repaired enough to manage the lane, but the current
vLLM-Metal runtime cannot load the model:

```text
ValueError: Model type qwen3_5 not supported.
```

The failing path is inside `mlx_vlm` through `vllm-metal`, after the controller
successfully rendered and bootstrapped the intended launchd command.

No `code-qwen36-shadow` alias was added. No public daily role alias was
promoted. OpenHands was not run because the direct backend gate failed.

## Runtime State
- Downloaded artifact:
  `mlx-community/Qwen3.6-27B-OptiQ-4bit`
- Resolved snapshot:
  `/Users/thestudio/models/hf/models--mlx-community--Qwen3.6-27B-OptiQ-4bit/snapshots/c8e1b620b9be2c03fd15fde261e25c9be8c664b7`
- Runtime overlay:
  `/Users/thestudio/models/hf/hub/runtime-overlays/mlx-qwen3-6-27b-optiq-4bit-qwen2-tokenizer`
- Served model target:
  `mlx-qwen3-6-27b-optiq-4bit`
- Intended lane:
  `com.bebop.mlx-lane.8101`
- Intended launch flags:
  `--max-model-len 32768`,
  `--no-async-scheduling`,
  `--enable-auto-tool-choice`,
  `--tool-call-parser qwen3_coder`,
  `--reasoning-parser qwen3`,
  `--language-model-only`

The overlay exists because the upstream tokenizer metadata declares
`tokenizer_class: TokenizersBackend`, which the current Transformers 4.x stack
does not load. The overlay only changes `tokenizer_config.json` to
`Qwen2TokenizerFast` and symlinks the downloaded snapshot files. It is a local
runtime workaround, not a model conversion.

After the failed launch, `mlxctl mlx-launch-stop --ports 8101` and
`mlxctl unload 8101 --no-sync` were run. `mlxctl verify` returned green, and
`8101` is stopped/disabled again.

## mlxctl Rescue Gate
The existing controller was not bypassed. The rescue gate stayed small:

- Fixed installed-copy repo-root discovery so `/Users/thestudio/bin/mlxctl`
  no longer tries to resolve `/platform/registry/services.jsonl`.
- Added `qwen36_coding` runtime profile defaults:
  `qwen3_coder`, `qwen3`, 32K context, no async scheduling, and
  `--language-model-only`.
- Added a compatibility `qwen3_coder_main` profile for existing registry rows.
- Taught preflight to fall back to vLLM's config registry when Transformers
  does not know a new architecture already supported by vLLM.
- Made the launchd plist writer use `/usr/bin/python3` under `sudo` to avoid
  the broken Homebrew Python 3.14 `plistlib`/`pyexpat` path on Studio.

`mlxctl status`, `vllm-render`, and `verify` now work from the Studio-installed
copy.

## Validation Performed
- Local targeted controller tests passed:
  `test_mlxctl_vllm_flags.py`,
  `test_mlxctl_state_model.py`,
  `test_mlx_runtime_profiles.py`
- `uv run python -m py_compile platform/ops/scripts/mlxctl` passed.
- Build worktree preflight passed.
- Studio disk check before download showed about `3.3 TiB` free and about
  `83 GiB` already used under `/Users/thestudio/models/hf`.
- Hugging Face artifact was public/non-gated at
  `c8e1b620b9be2c03fd15fde261e25c9be8c664b7`.
- Stale `8100` and `8102` launchd labels were disabled.
- Stale `8123` registry assignment was reconciled.
- GPT-OSS `8126` remained healthy through the work.

## Decision
Do not add the LiteLLM shadow alias in this slice. The current Studio
vLLM-Metal backend is not a viable serving path for this exact Qwen3.6 MLX
artifact until `mlx_vlm`/`vllm-metal` supports `qwen3_5`.

The next viable paths are:

- Re-test this same artifact only after the Studio vLLM-Metal stack advertises
  `qwen3_5` support in the actual MLX loader, not just vLLM's config registry.
- Use a GGUF/Q4 Qwen3.6 artifact through LM Studio or llama.cpp for a coding
  specialist smoke if native MLX support remains blocked.
- Keep `mlxctl v2` deferred. The existing controller was repairable for this
  gate, and the blocker is backend model support rather than controller shape.
