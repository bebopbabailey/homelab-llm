# Architecture: OptiLLM Proxy

OptiLLM runs as a Studio LAN-bound proxy at `192.168.1.72:4020` and is reached
by LiteLLM as an upstream. It applies optimization and strategy plugins before
forwarding upstream to Mini LiteLLM.
