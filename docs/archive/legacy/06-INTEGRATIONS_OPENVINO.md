# 06-INTEGRATIONS_OPENVINO

## OpenVINO backend launch details
- Service is a user systemd unit that runs uvicorn on port 9000 with host 0.0.0.0.
  Evidence: `/home/christopherbailey/.config/systemd/user/ov-server.service`
  ```
  ExecStart=/home/christopherbailey/.local/bin/uv run uvicorn main:app --host 0.0.0.0 --port 9000 --workers 1
  ```
- Runtime env file path:
  Evidence: `/home/christopherbailey/.config/ov-llm-server/ov-server.env`
  ```
  OV_DEVICE=GPU
  OV_REGISTRY_PATH=/home/christopherbailey/models/converted_models/registry.json
  OV_MODEL_PATH=/home/christopherbailey/models/converted_models/qwen2-5-3b-instruct/task-text-generation-with-past__wf-fp32
  ```

## API endpoints exposed by ov-llm-server
- `/health`, `/v1/models`, `/v1/chat/completions`
  Evidence: `/home/christopherbailey/ov-llm-server/main.py`
  ```
  @app.get("/health")
  @app.get("/v1/models")
  @app.post("/v1/chat/completions")
  ```

## LiteLLM targeting
- LiteLLM routes `lil-jerry` to the OpenVINO backend via env vars.
  Evidence: `/home/christopherbailey/litellm-orch/config/router.yaml`, `/home/christopherbailey/litellm-orch/config/env.local`
  ```
  LIL_JERRY_API_BASE=http://localhost:9000/v1
  LIL_JERRY_MODEL=openai/llama-3-2-3b-instruct
  LIL_JERRY_API_KEY=dummy
  ```

## Notes
- Docs claim OpenVINO is localhost-only, but the active systemd unit binds 0.0.0.0 (LAN-exposed).
  Evidence: `/home/christopherbailey/litellm-orch/docs/security.md` vs `/home/christopherbailey/.config/systemd/user/ov-server.service`
