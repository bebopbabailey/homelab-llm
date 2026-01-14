# Architecture: OptiLLM Proxy

OptiLLM runs as a localhost-only proxy that can be routed to by LiteLLM. It wraps
requests to apply optimization/strategy plugins before forwarding upstream.
