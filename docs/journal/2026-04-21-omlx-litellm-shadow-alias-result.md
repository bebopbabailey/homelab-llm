# 2026-04-21 - oMLX LiteLLM shadow-alias result

## Summary

The non-public LiteLLM shadow-alias follow-up for oMLX was attempted and
stopped. Direct oMLX remained strong, and the isolated LiteLLM alias worked at
first, but the LiteLLM path degraded during soak and then returned hard `500`
errors. Do not add an oMLX LiteLLM shadow alias yet.

Recommendation: **stop this integration path for now**. Keep direct oMLX as the
validated path; do not expose it through LiteLLM until the proxy failure mode is
understood and reproduced with a smaller diagnostic.

## Runtime shape

- Run dir: `/tmp/omlx-litellm-shadow-alias-20260421T231830Z`
- Studio oMLX listener: `127.0.0.1:8120`
- Mini SSH tunnel for direct parity: `127.0.0.1:8129` -> Studio `127.0.0.1:8120`
- Mini isolated LiteLLM shadow listener: `127.0.0.1:4012`
- Alias: `omlx-shadow-qwen3-4b-2507`
- Model: `mlx-community/Qwen3-4B-Instruct-2507-4bit`
- oMLX candidate: `jundot/omlx/omlx 0.3.6`
- Request path: `/v1/chat/completions` only
- No Open WebUI, canonical `fast`/`main`/`deep`, llmster, public routing, or
  launchd ownership changes were made.

## Key management

The DB-backed LiteLLM virtual-key path worked.

- `key_mode.txt`: `db_virtual_key`
- Generated key restriction: `models=["omlx-shadow-qwen3-4b-2507"]`
- Expiry in LiteLLM response: `2026-04-22T05:22:58.920477Z`
- Cleanup result: `key_delete_ok`

## Results

| Block | Success | p50 s | p95 s | max s | output tok/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| `warm-direct-S02` | 2/2 | 3.420 | 3.523 | 3.523 | 132.55 |
| `warm-shadow-S02` | 2/2 | 3.764 | 3.916 | 3.916 | 117.73 |
| `warm-direct-S04` | 2/2 | 3.180 | 3.552 | 3.552 | 97.42 |
| `warm-shadow-S04` | 2/2 | 3.792 | 4.131 | 4.131 | 87.14 |
| `sentinel-0-shadow-S02` | 2/2 | 3.790 | 3.900 | 3.900 | 119.76 |
| `sentinel-20-shadow-S02` | 2/2 | 4.716 | 4.933 | 4.933 | 93.46 |
| `soak-11-shadow-S04` | 2/2 | 7.892 | 8.431 | 8.431 | 41.04 |
| `soak-23-shadow-S04` | 0/2 | 2.747 | 2.748 | 2.748 | 0.00 |

Initial direct-vs-shadow parity was usable enough to continue into soak. During
soak, latency and throughput degraded materially, then the shadow path returned
two `500` responses in the same concurrent `S04` block.

## Blocker

The blocker is **LiteLLM proxy reliability in front of oMLX for this workload**.

The two failed `soak-23-shadow-S04` requests returned:

```text
litellm.InternalServerError: InternalServerError: OpenAIException - Expecting value: line 1 column 2 (char 1).
Received Model Group=omlx-shadow-qwen3-4b-2507
Available Model Group Fallbacks=None
```

LiteLLM logs show the exception in the OpenAI-compatible upstream response parse
path. The oMLX grep pass did not show a matching traceback, panic, or explicit
server-side error. That makes this an integration failure until proven
otherwise: LiteLLM received or parsed an upstream response it could not handle.

## Cleanup

- The restricted LiteLLM virtual key was deleted successfully.
- Mini listeners `4012` and `8129` were clear after cleanup.
- Studio listener `8120` was clear after cleanup.
- Studio cleanup telemetry showed swap use at `1.00M` and the oMLX shadow cache
  at `3.9G`.
- The repo worktree remained clean after the runtime attempt.

## Artifacts

This journal entry is the durable repo record. The `/tmp` artifacts below were
left as supporting local evidence from the run and should not be treated as
long-term storage.

- Block summaries: `/tmp/omlx-litellm-shadow-alias-20260421T231830Z/summary.jsonl`
- Per-request ledger: `/tmp/omlx-litellm-shadow-alias-20260421T231830Z/requests.jsonl`
- LiteLLM logs:
  `/tmp/omlx-litellm-shadow-alias-20260421T231830Z/litellm.stderr.log`,
  `/tmp/omlx-litellm-shadow-alias-20260421T231830Z/litellm.stdout.log`
- Manifest hash:
  `63d2537715592d3b946545e32f7a329c26b0613a90c838a9b3f95725bb8ca9e2`

## Follow-up

Before another shadow-alias attempt, isolate the LiteLLM parse failure with a
shorter repro:

- same model and same `/v1/chat/completions` request shape
- direct oMLX response body capture for the failing `S04` shape
- LiteLLM upstream raw-response capture, if available
- no four-hour soak until the parse failure is explained
