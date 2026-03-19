# llama-cpp-server

Repo-owned GPT service family for FAST/DEEP rollout.

Approved architecture:
- service boundary: `layer-inference/llama-cpp-server/`
- headless implementation: `llmster`
- inference architecture: llama.cpp
- canonical GPT artifacts: MXFP4 GGUF
- public LiteLLM aliases: `fast`, `deep`
- raw `llama-server` mirrors stay separate from the public service path

This boundary exists so the repo can treat the GPT backend as a durable service
contract instead of burying it inside ad hoc Studio notes.
