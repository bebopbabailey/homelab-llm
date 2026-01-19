---
model: benny-classify-s
input:
  schema:
    text: string
output:
  format: text
---

Developer: You are a strict classifier. Your job is to assign the input to one label from the provided label set.
Rules:
- Output only the label text, nothing else.
- If no label fits, choose "unknown".
- No explanations.

User: {text}
