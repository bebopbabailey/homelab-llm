# NOW — Transcript Reliability (Contract-First)

## Current focus
1) Upgrade mlx-openai-server to a supported release (target: 1.5.1) on Studio.
2) Ensure Harmony parsers + chat template are correctly applied for GPT-OSS models.
3) Verify MLX returns standard OpenAI-compatible `message.content` with reasoning optional.
4) Remove local response-shaping patch once verified.
5) Only then consider a minimal, supported post-cleaner if needed.

## NEXT UP
Enable LiteLLM UI access so client-side system prompts/presets can be managed there.

## Out of scope (for now)
- OptiLLM local inference (Studio)
- New model downloads/conversions
- New registries beyond presets/handles
