# 04-INTEGRATIONS_LITELLM

## LiteLLM configuration
- Routing config: `/home/christopherbailey/litellm-orch/config/router.yaml`
- Runtime env: `/home/christopherbailey/litellm-orch/config/env.local`
- Example template: `/home/christopherbailey/litellm-orch/config/env.example`

Evidence (router config):
```
model_list:
  - model_name: jerry-weak
    litellm_params:
      model: os.environ/JERRY_WEAK_MODEL
      api_base: os.environ/JERRY_WEAK_API_BASE
      api_key: os.environ/JERRY_WEAK_API_KEY
```

Evidence (router settings + logging):
```
router_settings:
  allowed_fails: 2
  cooldown_time: 15
  retry_policy:
    Timeout: 1
    APIConnectionError: 1
    RateLimitError: 0
    ServiceUnavailableError: 1

litellm_settings:
  json_logs: true
```

## Upstream definitions
- Upstream base URLs are provided via env vars and point to Studio MLX ports and local OpenVINO.
  Evidence: `/home/christopherbailey/litellm-orch/config/env.local`
  ```
  JERRY_CHAT_API_BASE=http://192.168.1.72:8100/v1
  JERRY_EDITOR_API_BASE=http://192.168.1.72:8101/v1
  JERRY_ARCHITECT_API_BASE=http://192.168.1.72:8102/v1
  JERRY_WEAK_API_BASE=http://192.168.1.72:8103/v1
  JERRY_TEST_API_BASE=http://192.168.1.72:8109/v1
  LIL_JERRY_API_BASE=http://localhost:9000/v1
  ```
- Model naming is plain in LiteLLM (`jerry-*`, `lil-jerry`), while upstream provider routing uses `openai/<upstream>`.
  Evidence: `/home/christopherbailey/litellm-orch/config/env.local`
  ```
  JERRY_CHAT_MODEL=openai/halley-ai/gpt-oss-120b-MLX-6bit-gs64
  LIL_JERRY_MODEL=openai/llama-3-2-3b-instruct
  ```

## Auth, logging, metrics
- Logging: JSON logs enabled via `litellm_settings.json_logs` in router config.
  Evidence: `/home/christopherbailey/litellm-orch/config/router.yaml`
- Proxy key enforcement is planned (not enabled in current config).
  Evidence: `/home/christopherbailey/litellm-orch/README.md`
  ```
  export LITELLM_PROXY_KEY="your-strong-key"
  ```

## Integration hooks for Tiny Agents (plan, no code)
- Add a new upstream entry using the existing env-driven pattern:
  1) Add `TINYAGENTS_API_BASE` and `TINYAGENTS_MODEL` to `config/env.local` (or a new env file) without changing ports in `02-PORTS_ENDPOINTS_REGISTRY.md`.
  2) Add a `model_list` entry in `config/router.yaml` with a new logical model name (for example, `tinyagents-router`) pointing to `os.environ/TINYAGENTS_API_BASE` and `os.environ/TINYAGENTS_MODEL`.
  3) Keep `litellm_params.model` prefixed with `openai/` if the upstream is OpenAI-compatible.
  4) Update `02-PORTS_ENDPOINTS_REGISTRY.md` and `07-SECURITY_BOUNDARIES.md` before any new LAN exposure.
  5) Validate with `GET /v1/models` and `POST /v1/chat/completions` against the new model name.
- This plan mirrors the existing `model_list` + env substitution pattern.
  Evidence: `/home/christopherbailey/litellm-orch/config/router.yaml`

## LiteLLM base URL recommendation (Tiny Agents clients)
- Prefer `http://mini:4000` only if name resolution for `mini` is configured (DNS or hosts entry).
  - Benefits: stable name, avoids IP changes, still explicit to the host.
  - Fallback: `http://192.168.1.71:4000` if name resolution is unavailable.
  Evidence: user confirmation of `ssh mini` alias and LiteLLM port 4000.
