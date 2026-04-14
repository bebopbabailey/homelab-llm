---
name: repo-plan-review
description: Review a repo plan for drift, missing tests, failure handling, and simplification opportunities
compatibility: opencode
---

## What I do

- Review plans against the repo contract and current runtime truth.
- Look for drift against service docs, gateway/runtime contracts, and testing expectations.
- Tighten acceptance criteria, rollback paths, and failure-mode coverage.

## Review checklist

- Does the plan match the current active runtime and alias surface?
- Does it keep service boundaries intact and avoid hidden cross-layer work?
- Are verification steps concrete and sufficient for the touched surface?
- Are rollback and fallback behaviors explicit?
- Is there a simpler implementation path that preserves the goal?
- Are any assumptions unproven by repo evidence?

## Output shape

- Findings first.
- Then a revised plan.
- Then confidence and any remaining assumptions.
