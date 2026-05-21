# Architecture: omlx-agent-gateway

`omlx-agent-gateway` is a Mini-local compatibility surface for agent framework
experiments that need an OpenAI-style URL but should not depend on LiteLLM.

Flow:

```text
agent framework / operator harness
-> http://127.0.0.1:4022/v1
-> omlx-agent-gateway
-> http://192.168.1.72:8120/v1
-> Studio oMLX Qwen3.6 primitive
```

The gateway does not own inference, scheduling, tool execution, MCP lifecycle,
fallbacks, or response repair. oMLX remains the backend source of truth.

