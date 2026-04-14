# OptiLLM Proxy — Overview & Usage

## What this service is
OpenAI-compatible optimizing inference proxy used behind LiteLLM `boost`.

## Placement in the homelab
Client(s) -> LiteLLM (Mini) -> OptiLLM (Studio LAN `192.168.1.72:4020`) ->
LiteLLM (Mini LAN) -> real backends.

## Contract
- LiteLLM is the approved caller in this repo.
- Direct end-user or app-client integration is out of contract for the current
  deployment.
- Current Studio deployment does not require listener bearer auth; protection is
  by the dedicated LAN bind plus the LiteLLM-only caller contract.

## Strategy selection
Use `optillm_approach` in the request body when calling through the LiteLLM
`boost` path or during operator-only direct verification.

## Provider config
`~/.optillm/proxy_config.yaml`
```yaml
providers:
  - name: litellm
    base_url: http://192.168.1.71:4000/v1
    api_key: "${OPENAI_API_KEY}"
```

## Verification checklist
- OptiLLM responds to `/v1/models` on `192.168.1.72:4020`
- Requests via LiteLLM `boost` reach OptiLLM
- OptiLLM makes upstream calls to Mini LiteLLM
- No routing loops occur
