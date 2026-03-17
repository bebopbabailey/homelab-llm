# Websearch Eval Summary

## Inputs
- `evals/websearch/artifacts/20260308T193329Z-baseline-deep-freshness-high-extra.json`
- blocked domains: `evals/websearch/blocked_domains.txt`

## Totals
- Results: 4
- Providers: owui-research

## Categories
- `freshness-current`: 3
- `weak-model-stress`: 1

## Category Breakdown By Provider
| category | owui-research |
| --- | ---: |
| freshness-current | 3 |
| weak-model-stress | 1 |

## Provider Breakdown
### owui-research
- Cases: 4
- Errors: 0
- Assertion failures: 0
- Empty outputs: 0
- Zero-source cases: 0
- Blocked-domain hits: 0
- Smoke latency diagnostics (>= 120000 ms): 0
- Median latency ms: 17571.11
- P95 latency ms: 21439.17
- Top domains:
  - `www.reddit.com`: 3
  - `en.wikipedia.org`: 2
  - `www.foxnews.com`: 1
  - `www.nbcnews.com`: 1
  - `news.google.com`: 1
  - `apnews.com`: 1
  - `www.nytimes.com`: 1
  - `www.cnn.com`: 1
  - `askubuntu.com`: 1
  - `www.firefox.com`: 1
