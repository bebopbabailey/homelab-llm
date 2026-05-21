# oMLX Agent Gateway

Mini-local localhost gateway for the Studio oMLX Qwen3.6 agent backend
primitive. It exposes a minimal OpenAI-compatible surface for future agent
framework experiments without adding a LiteLLM alias or public daily route.

The gateway supports non-streaming chat completions and streaming
server-sent-event passthrough for agent clients that require `stream=true`.
