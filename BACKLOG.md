# BACKLOG

Short list of future work not active right now.

## Nice-to-haves
- Confirm alias naming and mapping (main / deep / fast / swap, + x1..x4).
- Validate preset behavior via LiteLLM/OptiLLM (routing, chain applied, responses).
- Keep OpenCode config aligned with current handles and tool access.
- Open WebUI preset sync from LiteLLM presets.
- Enable LiteLLM UI access so client-side system prompts/presets can be managed there.
- Formalize a presets registry (JSONL + validator + CLI).
- Document SDLC mapping and usage guidance.
- Transcript pipeline service (server-side chaining, stateless + stateful interviewer, SQLite persistence, strict JSON outputs).
- Inference benchmarking framework (latency/quality journal automation).
- Model table design (database-backed, size-on-disk + idle-memory fields).
- OptiLLM local inference (Studio) for decode-time techniques.
- Optional second-pass tone classification for transcripts (separate endpoint).
- OV router service (OpenVINO-backed router classifier for OptiLLM).
- OptiLLM router caching follow-up (re-verify after any OV work).
