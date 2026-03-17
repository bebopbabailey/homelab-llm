# Websearch Eval Summary

## Inputs
- `evals/websearch/artifacts/20260308T193329Z-baseline-fast-freshness-high-extra.json`
- blocked domains: `evals/websearch/blocked_domains.txt`

## Totals
- Results: 4
- Providers: owui-fast

## Categories
- `freshness-current`: 3
- `weak-model-stress`: 1

## Category Breakdown By Provider
| category | owui-fast |
| --- | ---: |
| freshness-current | 3 |
| weak-model-stress | 1 |

## Provider Breakdown
### owui-fast
- Cases: 4
- Errors: 0
- Assertion failures: 0
- Empty outputs: 0
- Zero-source cases: 0
- Blocked-domain hits: 0
- Smoke latency diagnostics (>= 120000 ms): 0
- Median latency ms: 19217.20
- P95 latency ms: 25403.01
- Top domains:
  - `www.reddit.com`: 3
  - `history.state.gov`: 1
  - `www.xvideos.com`: 1
  - `www.xvideos.tube`: 1
  - `www.pornhub.com`: 1
  - `dailythemedcrosswordanswers.com`: 1
  - `askubuntu.com`: 1
  - `github.com`: 1
  - `docs.searxng.org`: 1
  - `en.wikipedia.org`: 1
