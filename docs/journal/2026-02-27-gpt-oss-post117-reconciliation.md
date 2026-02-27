# 2026-02-27 — GPT-OSS post-117 result reconciliation (chat + journal correction)

## Why this entry exists
Recent chat turns mixed two evidence windows:
- older codified entries showing GPT-OSS overlap failure (`c2` crash),
- newer post-117 artifacts showing successful overlap runs for tuned configs.

This entry resolves that conflict explicitly and supersedes stale conclusions.

## Source windows
### Window A (older, still true for that time window)
- `docs/journal/2026-02-26-vllm-metal-8120-fast-targeted-phasea-results.md`
- `docs/journal/2026-02-26-vllm-metal-8122-deep-targeted-phasea-results.md`
- Conclusion then: `broadcast_shapes` crash at overlap (`c2`) on GPT-OSS lanes.

### Window B (newer post-117 artifacts)
- `/tmp/vllm_metal_fast_post117.json`
- `/tmp/vllm_metal_fast_post117.md`
- `/tmp/vllm_metal_deep_post117_retry.json`
- `/tmp/vllm_metal_deep_post117_retry.md`
- `/tmp/vllm_metal_deep_65536_recheck_after_fix.json`

## Reconciled findings (current)
1. `metal-test-fast` (`8120`)
- Post-117 targeted run shows overlap viability in tuned configs (`c4` measured, PASS).
- Practical tuned posture remains:
  - `VLLM_METAL_MEMORY_FRACTION=0.60`
  - `--no-async-scheduling`
  - `max_model_len` in tested passing set (`32768/65536/131072`) with winner recorded as `32768`.

2. `metal-test-deep` (`8122`)
- Post-117 evidence is mixed but positive:
  - at least one strong overlap PASS (`32768 + 0.60`, `c4` measured),
  - focused `65536 + 0.60` recheck also PASS in dedicated rerun artifact.
- Not all candidate variants pass in the retry matrix; keep this as "works in tuned lanes, validate per profile."

3. `metal-test-main` (`8121`)
- Separate crash class (async scheduler path) remains addressed by:
  - `--no-async-scheduling`
  - canonical tuned setting from closure:
    `mem_fraction=0.60`, `max_model_len=65536`.

## Correction to prior statements
- Prior statement "GPT-OSS must be treated as concurrency=1 only" is now outdated
  for the post-117 tuned runs.
- Correct current statement:
  - GPT-OSS overlap (`concurrency>1`) is viable in the tested tuned post-117 configs,
    with deep lane still requiring profile-specific validation due to mixed matrix outcomes.

## Follow-up doc hygiene
- Keep 2026-02-26 entries as historical snapshots (not deleted).
- Treat this entry as the active interpretation layer for post-117 behavior.
