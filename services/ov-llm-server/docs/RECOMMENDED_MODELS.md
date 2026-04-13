# Recommended Models for This Hardware

This Mac Mini (Intel i7 + iGPU, 64 GB RAM) is best suited to small and mid-sized
instruction models. For fast local inference, prioritize 3B-class models, and
use 7B only when you need higher quality.

## Selection Criteria
- **Speed first**: smaller models (1–3B) respond faster on iGPU.
- **Quality when needed**: 7B models for better reasoning at higher latency.
- **OpenAI-compatible tasks**: instruction following, classification, tool-style prompting.

## Fast Tier (Primary Use)
These are the fastest and most practical for always-on use.

### Qwen/Qwen2.5-3B-Instruct
- **Purpose**: general instruction following and short responses
- **Strengths**: strong quality for size, good for classification-style prompts
- **Use when**: you want quick, reliable answers with low latency

### meta-llama/Llama-3.2-3B-Instruct
- **Purpose**: general reasoning and instruction following
- **Strengths**: balanced quality, stable behavior for structured prompts
- **Use when**: you want a second “opinion” model at similar speed

### microsoft/Phi-4-mini-instruct
- **Purpose**: concise reasoning and structured outputs
- **Strengths**: good at short, focused tasks and templated output
- **Use when**: you want very short, direct answers

## Quality Tier (Slower, Better Depth)
Use these when you can accept higher latency.

### mistralai/Mistral-7B-Instruct-v0.3
- **Purpose**: deeper instruction following and more nuanced responses
- **Strengths**: stronger coherence and reasoning vs 3B models
- **Use when**: you need higher-quality synthesis, summaries, or multi-step output

## Notes on Tool Calling
This server uses prompt-based tool calling. Models do not need native tool-calling
support; they just need to reliably produce JSON-like outputs when instructed.

## Suggested Usage Pattern
- Default to a 3B model for most requests.
- Escalate to 7B only for deeper reasoning or higher stakes outputs.
- Keep a second 3B model as a “specialist” for cross-checking.
