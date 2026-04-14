---
description: Critique and refine a repo plan with the experimental ChatGPT/Codex reviewer lane
agent: repo-codex-review
model: litellm/chatgpt-5
---

Review the following repo plan or design note.

Task:
$ARGUMENTS

Required output:

## Findings
- List the concrete weaknesses, drift risks, and missing checks first.

## Revised Plan
- Provide a tightened replacement plan only after the findings.

## Confidence
- High / Medium / Low with one sentence.

Rules:
- Do not edit files.
- Do not inspect the repo or call tools.
- Prefer critique and refinement over full replacement.
- Call out any assumptions that are not proven by the supplied text.
