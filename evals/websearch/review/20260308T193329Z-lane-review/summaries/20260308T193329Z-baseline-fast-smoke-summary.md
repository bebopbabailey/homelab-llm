# Websearch Eval Summary

## Inputs
- `evals/websearch/artifacts/20260308T193329Z-baseline-fast-smoke.json`
- blocked domains: `evals/websearch/blocked_domains.txt`

## Totals
- Results: 13
- Providers: owui-fast

## Categories
- `adversarial-junk`: 2
- `freshness-current`: 3
- `long-tail-factual`: 2
- `product-research`: 2
- `technical-docs`: 2
- `weak-model-stress`: 2

## Category Breakdown By Provider
| category | owui-fast |
| --- | ---: |
| adversarial-junk | 2 |
| freshness-current | 3 |
| long-tail-factual | 2 |
| product-research | 2 |
| technical-docs | 2 |
| weak-model-stress | 2 |

## Provider Breakdown
### owui-fast
- Cases: 13
- Errors: 0
- Assertion failures: 0
- Empty outputs: 0
- Zero-source cases: 0
- Blocked-domain hits: 0
- Smoke latency diagnostics (>= 120000 ms): 0
- Median latency ms: 24130.29
- P95 latency ms: 39343.33
- Top domains:
  - `www.merriam-webster.com`: 4
  - `www.thefreedictionary.com`: 4
  - `www.zhihu.com`: 3
  - `en.wikipedia.org`: 3
  - `news.google.com`: 3
  - `dictionary.cambridge.org`: 3
  - `github.com`: 2
  - `www.foxnews.com`: 2
  - `www.nbcnews.com`: 2
  - `apnews.com`: 2
- Likely junk domains:
  - `www.zhihu.com`: 3
  - `ell.stackexchange.com`: 2
  - `english.stackexchange.com`: 1
