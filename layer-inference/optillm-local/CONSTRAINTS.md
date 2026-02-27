# Constraints: optillm-local (experimental)

## Hard constraints
- Experimental workspace only; do not alter production LiteLLM/OptiLLM/MLX services.
- No new LAN exposure. Bind experimental server to `127.0.0.1` only.
- Keep upstream patch surface minimal (few files, additive changes).
- No dependency/lockfile churn unless explicitly required for the experiment.

## API constraints
- Preserve OpenAI-ish HTTP compatibility for chat/completions.
- New request fields must be additive and optional.
- Default behavior must remain unchanged when decode fields are absent.

## Rollout constraints
- Non-streaming decode techniques first.
- Streaming support is a later milestone.
- LiteLLM integration is deferred until isolated viability is proven.
