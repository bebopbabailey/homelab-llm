# 2026-05-20 - Pi local Qwen scratch smoke

## Objective
Evaluate whether `pi-coding-agent` can drive the Mini-local oMLX Qwen3.6
sidecar as a coding agent on one disposable scratch-repo bugfix task.

## Runtime Shape
- Playground:
  `/home/christopherbailey/pi-qwen-trials/20260520-local-qwen-smoke`
- Scratch repo:
  `/home/christopherbailey/pi-qwen-trials/20260520-local-qwen-smoke/scratch-repo`
- Pi install:
  `/home/christopherbailey/pi-qwen-trials/20260520-local-qwen-smoke/pi-tooling`
- Pi isolated config:
  `/home/christopherbailey/pi-qwen-trials/20260520-local-qwen-smoke/pi-config/models.json`
- Pi provider/model:
  `local-qwen` / `omlx-qwen36-27b-optiq-4bit`
- Sidecar:
  `http://127.0.0.1:4022/v1`
- Studio upstream:
  `omlx-qwen36-27b-optiq-4bit` on Studio oMLX `8120`

The Pi config used `api: "openai-completions"` with local compatibility flags
for no developer role, no reasoning effort, no streaming usage, and
`max_tokens`.

## Result
Success after one small compatibility patch.

The first Pi run reached the sidecar but stopped immediately:

```text
400 stream=true is unsupported for this primitive gateway
```

Pi requires OpenAI streaming for this mode. The sidecar was updated to pass
`stream=true` chat completions through as server-sent events. After that change,
Pi completed the scratch task through local Qwen.

## Scratch Task
The scratch repo contained a small `tinycalc` package with a failing stdlib
`unittest`:

```text
test_rejects_reversed_intervals ... FAIL
AssertionError: ValueError not raised
```

Pi inspected the scratch repo, ran the failing test, edited only
`src/tinycalc/intervals.py`, and added validation for reversed intervals:

```python
for start, end in intervals:
    if start > end:
        raise ValueError(
            f"Invalid interval ({start}, {end}): start must be <= end"
        )
```

Final validation:

```text
Ran 3 tests in 0.000s

OK
```

## Evidence
- Initial failed Pi run:
  `artifacts/pi-run.jsonl`
- Successful Pi run:
  `artifacts/pi-run-after-stream-patch.jsonl`
- Baseline failing test:
  `artifacts/baseline-unittest-after-reset.log`
- Final passing test:
  `artifacts/final-unittest.log`
- Final scratch diff:
  `artifacts/final-diff.patch`
- Sidecar streaming smoke:
  `artifacts/sidecar-stream-smoke.sse`

All artifact paths are under:
`/home/christopherbailey/pi-qwen-trials/20260520-local-qwen-smoke`.

## Decision
Pi is viable enough for the next evaluation slice with local Qwen. The key
finding is that the Mini sidecar must support streaming passthrough for Pi and
likely other coding-agent clients.

Recommended next slice: evaluate a Kanban/control layer around the now-proven
Pi + local-Qwen path, rather than adding LiteLLM, OpenHands, or a larger harness
first.
