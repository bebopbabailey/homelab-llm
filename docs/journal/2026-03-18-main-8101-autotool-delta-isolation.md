# 2026-03-18 — Canonical `8101` Qwen auto-tool delta isolation

## Summary
- Re-ran the canonical `8101` Qwen lane under the corrected managed `mlxctl`
  contract.
- Proved that the original `8101` regression was partly a control-plane render
  problem:
  - old render used `65536`
  - old render forced a local `chat_template.jinja`
  - old render omitted `--generation-config vllm`
- Fixed the managed render so `8101` now launches with:
  - `--max-model-len 32768`
  - `--generation-config vllm`
  - `--no-async-scheduling`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser hermes`
  - no explicit `--chat-template`
  - `VLLM_METAL_MEMORY_FRACTION=auto`
- Even after that correction, direct `tool_choice="auto"` on canonical `8101`
  still failed to return parsed `tool_calls`.
- The endpoint instead emitted raw `<tool_call>...</tool_call>` markup in
  assistant `content`, and logs showed `hermes_tool_parser.py` raising
  `KeyError: 'name'`.

## What changed in control plane
- Updated the `qwen3_main` runtime profile defaults to:
  - `tool_call_parser=hermes`
  - `reasoning_parser=null`
  - `chat_template_strategy=tokenizer`
  - `generation_config=vllm`
- Updated `mlxctl` vLLM flag compilation to support `generation_config`.
- Stopped auto-seeding a local `chat_template` into Qwen3 entries during
  defaulting.
- Reloaded Studio `8101` with the corrected managed render.

## Direct backend evidence
### Canonical `8101`
- `GET /v1/models`: PASS
- structured outputs smoke: PASS
- `tool_choice="auto"` repeated probe (`5/5` sampled): FAIL
  - `tool_calls`: empty
  - `content`: raw `<tool_call>...</tool_call>`
  - no `5xx`
  - no timeout

### Live `8101` launchd argv after fix
- `--max-model-len 32768`
- `--generation-config vllm`
- `--no-async-scheduling`
- `--enable-auto-tool-choice`
- `--tool-call-parser hermes`
- no `--chat-template`

## Log evidence
Current canonical `8101` logs show:

```text
ERROR ... hermes_tool_parser.py ... KeyError: 'name'
```

This confirms the remaining failure is no longer the old explicit-template /
generation-config mismatch. It is now a parser/runtime behavior problem on the
current `vllm-metal` build under the canonical lane.

## Gateway result
- LiteLLM was kept healthy.
- Active public LLM alias surface remains exactly:
  - `main`
  - `fast`
  - `deep`
- `main` structured outputs through LiteLLM: PASS
- `fast` basic chat through LiteLLM: PASS
- `deep` basic chat through LiteLLM: PASS

## Current interpretation
- The `8101` control-plane contract is now aligned with the intended Qwen
  managed-lane shape.
- That alignment did not restore parsed `tool_calls` for `tool_choice="auto"`.
- The remaining defect is narrowed to runtime behavior on the canonical lane,
  not the obvious launch-contract mismatch that existed before this pass.

## Next step
- Re-establish whether experimental `8123` still reproduces parsed
  `tool_calls` under the same corrected contract.
- If `8123` still passes while `8101` still fails, treat the defect as a
  canonical managed-lane/runtime-context delta.
- If `8123` no longer passes either, treat the earlier shadow success as
  non-durable runtime drift and stop claiming a real `8123` vs `8101` split.
