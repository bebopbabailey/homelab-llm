# Websearch Eval Summary

## Inputs
- `evals/websearch/artifacts/20260308T193329Z-baseline-deep-smoke.json`
- blocked domains: `evals/websearch/blocked_domains.txt`

## Totals
- Results: 13
- Providers: owui-research

## Categories
- `adversarial-junk`: 2
- `freshness-current`: 3
- `long-tail-factual`: 2
- `product-research`: 2
- `technical-docs`: 2
- `weak-model-stress`: 2

## Category Breakdown By Provider
| category | owui-research |
| --- | ---: |
| adversarial-junk | 2 |
| freshness-current | 3 |
| long-tail-factual | 2 |
| product-research | 2 |
| technical-docs | 2 |
| weak-model-stress | 2 |

## Provider Breakdown
### owui-research
- Cases: 13
- Errors: 0
- Assertion failures: 0
- Empty outputs: 0
- Zero-source cases: 0
- Blocked-domain hits: 0
- Smoke latency diagnostics (>= 120000 ms): 0
- Median latency ms: 24199.37
- P95 latency ms: 35750.04
- Top domains:
  - `www.zhihu.com`: 4
  - `www.merriam-webster.com`: 3
  - `dictionary.cambridge.org`: 3
  - `www.yourdictionary.com`: 3
  - `github.com`: 2
  - `en.wikipedia.org`: 2
  - `askubuntu.com`: 2
  - `unix.stackexchange.com`: 2
  - `support.google.com`: 2
  - `www.bestbuy.com`: 2
- Likely junk domains:
  - `www.zhihu.com`: 4
  - `unix.stackexchange.com`: 2
