# Review Priority Guide

Use this file to avoid scoring everything blindly.

## Best first pass
Score these queries first. They carry the most signal for the lane decision.

### Smoke slice
Open: `smoke.md`
Fill: `smoke-review.csv`

1. `ws-001` — latest Open WebUI release notes
- What to look for: whether either lane finds real upstream release-note sources instead of low-value junk.
- Current issue: both lanes leaned on `www.zhihu.com` and failed to answer well.
- Scoring emphasis:
  - usefulness
  - citation quality
  - junk-domain resistance

2. `ws-006` — latest Raspberry Pi OS release notes
- What to look for: whether the lane finds official distro/vendor sources and answers the actual question.
- Current issue: `owui-fast` pulled obviously wrong domains and produced a poor response.
- Scoring emphasis:
  - usefulness
  - citation quality
  - freshness

3. `ws-007` — Open WebUI SearXNG setup docs
- What to look for: collateral damage risk for technical documentation queries.
- Current issue: `owui-research` drifted into irrelevant generic build instructions and junky domains.
- Scoring emphasis:
  - usefulness
  - citation quality
  - junk-domain resistance

### Freshness-high-extra slice
Open: `freshness-high-extra.md`
Fill: `freshness-high-extra-review.csv`

4. `ws-003` — today's NVIDIA H200 pricing trend
- What to look for: whether the lane avoids explicit junk and acknowledges missing evidence cleanly.
- Current issue: `owui-fast` surfaced explicit domains; `owui-research` looked cleaner.
- Scoring emphasis:
  - junk-domain resistance
  - freshness
  - usefulness

5. `ws-004` — recent Firefox release security fixes
- What to look for: preference for Mozilla/offical sources and current security-fix framing.
- Current issue: `owui-fast` was badly contaminated by crossword/junk sources.
- Scoring emphasis:
  - citation quality
  - freshness
  - usefulness

6. `ws-005` — this week's OpenAI API changelog
- What to look for: whether the lane can detect weak evidence without hallucinating, while still surfacing the right source expectations.
- Current issue: both lanes leaned on Reddit-only evidence.
- Scoring emphasis:
  - usefulness
  - citation quality
  - freshness

7. `ws-032` — two recent sources about SearXNG privacy improvements
- What to look for: synthesis quality when the lane has to compare multiple sources and classify the change.
- Current issue: good stress test for whether `deep` is actually better than `fast`.
- Scoring emphasis:
  - usefulness
  - citation quality
  - freshness

## Suggested scoring order
1. Score the 3 smoke queries above.
2. Score the 4 freshness queries above.
3. If the lane winner is already obvious, stop there and ask for the rollup.
4. If the lane winner is still unclear, finish the remaining rows in `smoke-review.csv` and `freshness-high-extra-review.csv`.

## Fast heuristics
- `usefulness_score=5`: directly answers the question with strong grounding.
- `usefulness_score=3`: partially answers, hedges, or misses key details.
- `usefulness_score=1`: wrong, empty, or clearly not useful.

- `citation_quality_score=5`: mostly official/vendor/reference sources.
- `citation_quality_score=3`: mixed quality or weak supporting domains.
- `citation_quality_score=1`: junk, irrelevant, or obviously poor sources.

- `freshness_score=5`: clearly current and responsive to a time-sensitive query.
- `freshness_score=3`: partially current or uncertain.
- `freshness_score=1`: stale, evasive, or unsupported for a freshness-sensitive query.

- `junk_domain_score=5`: no meaningful junk contamination.
- `junk_domain_score=3`: mixed or somewhat noisy source set.
- `junk_domain_score=1`: obvious junk/spam/low-value contamination.

## Decision shortcut
- If `owui-research` is not clearly better on `ws-003`, `ws-004`, and `ws-032`, it probably does not justify becoming the default lane.
- If `owui-fast` keeps losing badly on junk-domain resistance while `owui-research` stays cleaner, that is the strongest argument for promoting `deep`.
