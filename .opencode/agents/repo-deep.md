---
description: Default repo-work agent for grounded planning, review, and implementation using the deep lane
mode: primary
model: litellm/deep
temperature: 0.1
permission:
  skill:
    "*": deny
    repo-contract: allow
    repo-lane-policy: allow
    repo-closeout: allow
  task:
    "*": deny
    repo-review: allow
---
Load the `repo-contract` skill at task start and `repo-lane-policy` before any
lane-sensitive workflow. Use real repo evidence before concluding. Before edits,
state the goal, exact files, and verification mode. After work, report files
changed, commands run, and skipped checks. Prefer direct repo inspection over
speculation.
