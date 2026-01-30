# NOW — Transcript Reliability (Contract-First)

## Current focus
1) Upgrade mlx-openai-server to 1.5.1 on Studio. (done)
2) Ensure Harmony parsers + chat template are correctly applied for GPT-OSS models. (done)
3) Verify MLX returns standard OpenAI-compatible `message.content` with reasoning optional. (done)
4) Remove local response-shaping patch once verified. (done; using supported config)
5) Set sane `max_tokens` defaults for GPT-OSS handles in LiteLLM. (done; 2048)
6) Only then consider a minimal, supported post-cleaner if needed. (done; task-only post-cleaner guardrail)

## NEXT UP
Enable LiteLLM UI access so client-side system prompts/presets can be managed there.

## Out of scope (for now)
- OptiLLM local inference (Studio)
- New model downloads/conversions
- New registries beyond presets/handles
