---
name: repo-lane-policy
description: Choose the safe OpenCode lane for this repo and fail closed when a lane cannot gather evidence
compatibility: opencode
---

## Lane policy

- `repo-deep` is the default for repo inspection, planning, review, and editing.
- `repo-main` is a canary lane for the same work, but it must fail closed if it
  does not gather real repo evidence.
- `repo-fast` is synthesis-only and must not inspect the repo or edit files.

## Enforcement

- Never treat format-compliant output without repo evidence as verified.
- If the chosen lane fails to gather evidence, say so explicitly and recommend
  the next safe lane.
- Do not silently switch lanes inside a response.
