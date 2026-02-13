  # TinyAgents Request Flow Examples

This file shows practical examples for the local TinyAgents service.

Service base:
- `http://127.0.0.1:4030`

## 1) Success case (`POST /run`)

Request:

```bash
curl -fsS http://127.0.0.1:4030/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "main",
    "messages": [
      {"role": "user", "content": "openvino llm"}
    ],
    "max_tool_calls": 1
  }' | jq .
```

Example response shape:

```json
{
  "run_id": "run-0f1b1f34-ec6e-4f6b-a7a0-3aaf5f537f19",
  "model": "main",
  "tool_calls": [
    {
      "tool_name": "search.web",
      "input_json": {
        "query": "openvino llm",
        "max_results": 3
      },
      "output_json": {
        "content": "..."
      },
      "error": null
    }
  ],
  "final_message": {
    "role": "assistant",
    "content": "OpenVINO LLM overview..."
  },
  "stats": {
    "usage": {
      "prompt_tokens": 123,
      "completion_tokens": 88,
      "total_tokens": 211
    }
  }
}
```

## 2) Error case (unknown allowed tool)

Request:

```bash
curl -sS http://127.0.0.1:4030/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "main",
    "messages": [
      {"role": "user", "content": "test"}
    ],
    "allowed_tools": ["not.real.tool"],
    "max_tool_calls": 1
  }' | jq .
```

Example response shape:

```json
{
  "detail": "Unknown allowed_tools: not.real.tool"
}
```

## 3) Health check

```bash
curl -fsS http://127.0.0.1:4030/health | jq .
```

Expected:

```json
{"status":"ok"}
```
