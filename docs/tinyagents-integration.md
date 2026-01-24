# TinyAgents Integration Notes (Planned)

TinyAgents will be an orchestration layer that calls LiteLLM as its single LLM API.
LiteLLM remains the only network‑exposed model gateway; TinyAgents should not call
backend MLX/OpenVINO endpoints directly.

## Expected IO Path
1. Client or service → TinyAgents
2. TinyAgents → LiteLLM (`http://192.168.1.71:4000`)
3. LiteLLM → MLX/OpenVINO backends

## Model Names
TinyAgents should call the **plain** logical model names exposed by LiteLLM:
`mlx-*`, `ov-*`.

## Responsibility Split
- **TinyAgents**: model selection, task decomposition, tool orchestration, task‑level retries.
- **LiteLLM**: upstream routing, health checks, cooldowns, request logging.

## Logging & Telemetry
LiteLLM emits JSONL logs; TinyAgents should log its own task traces separately and
link to LiteLLM request IDs when possible.

## Auth (Future)
When API keys are enabled, TinyAgents will send the LiteLLM proxy key as a bearer token. 
