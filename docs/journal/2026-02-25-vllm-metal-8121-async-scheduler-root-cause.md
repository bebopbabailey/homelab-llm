# 2026-02-25 — vLLM-metal `8121` root cause: async scheduler crash path

## Goal
Explain why `metal-test-main` (`8121`) intermittently failed with
`EngineCore encountered an issue` and validate a mitigation that keeps the lane
up under the same repro load.

## Scope
- Path tested: `OpenWebUI/LiteLLM -> metal-test-main -> Studio:8121`
- Hosts: Mini (`litellm-orch` logs), Studio (`vllm-8121.log`, listeners/process)
- Experimental ports only (`8120-8139`), no `mlxctl` lane changes.

## Baseline
- After Studio reboot, only `4020` was listening; `8120/8121/8122` were not
  auto-running.
- Relaunched all three vLLM-metal lanes manually (`8120`, `8121`, `8122`).
- Verified all lanes served `/v1/models`.

## Reproduction Matrix (key results)
- Direct to `8121` passed:
  - `n=1`, `max_tokens=16384`, short prompt
  - `n=1`, long history (~6k prompt tokens), `max_tokens=4096`
- LiteLLM single-flight also passed for the same shapes.
- Failure reproduced with overlap:
  - `n=1`, long context (~63k chars), `max_tokens=16384`, `concurrency=2`
  - Both requests returned 500 and `8121` listener disappeared.

Artifacts:
- `/tmp/8121_direct_matrix.json`
- `/tmp/8121_litellm_matrix.json`
- `/tmp/8121_overlap_stress.json`

## Root Cause Evidence (high confidence)
From Studio `/Users/thestudio/vllm-8121.log` at `2026-02-25 13:00:10 CST`:
- `EngineCore encountered a fatal error`
- traceback ends in:
  - `vllm/v1/core/sched/async_scheduler.py`, assertion:
    `assert request.num_output_placeholders >= 0`
- then:
  - `EngineDeadError: EngineCore encountered an issue`
  - API server emits `500 Internal Server Error`
  - API server shuts down and `8121` listener disappears.

This repro was **not** an OS SIGKILL/OOM event in this run; it was an internal
engine assertion path.

## Mitigation Tested
Relaunched `8121` with async scheduling disabled:

```bash
... vllm serve ... --port 8121 --no-async-scheduling
```

Validation after mitigation:
- Re-ran the previous crashing repro (`n=1`, long context, `concurrency=2`,
  repeated twice): all requests returned 200.
- `8121` listener stayed up.

Artifacts:
- `/tmp/8121_async_off_retest.json`

## Additional Stress Check
- Re-ran historical heavy pattern:
  - long context + `n=4`, `max_tokens=1886`, `concurrency=2`
- Result: both requests 200, listener remained up (slow but stable).

## Operational Takeaway
- The dominant failure mode observed here is an async scheduler assertion path
  under overlapping heavy decode workload, not simply "too many tokens."
- For current experimental operation of `metal-test-main`, launch with
  `--no-async-scheduling` until upstream behavior is validated as fixed.

## Commands Run
```bash
# Baseline
ssh studio "lsof -nP -iTCP -sTCP:LISTEN | egrep ':8120|:8121|:8122|:4020' || true"
ssh studio "ps -eo pid,ppid,etime,%cpu,%mem,rss,command | egrep 'vllm serve|8120|8121|8122' | grep -v egrep || true"

# Relaunch lanes
ssh studio "nohup ... --port 8120 > /Users/thestudio/vllm-8120.log 2>&1 &"
ssh studio "nohup ... --port 8121 > /Users/thestudio/vllm-8121.log 2>&1 &"
ssh studio "nohup ... --port 8122 > /Users/thestudio/vllm-8122.log 2>&1 &"

# Matrix runs
uv run python - <<'PY' ... direct 8121 matrix ... PY
uv run python - <<'PY' ... LiteLLM matrix ... PY
uv run python - <<'PY' ... overlap stress ... PY

# Mitigation run + validation
ssh studio "pkill -f '/port 8121' || true; nohup ... --port 8121 --no-async-scheduling > /Users/thestudio/vllm-8121.log 2>&1 &"
uv run python - <<'PY' ... async-off repro retest ... PY
```

## Verification Mode
- FAST (runtime forensics + targeted repro + mitigation retest)

## Status
- PASS for root-cause identification and mitigation validation.
