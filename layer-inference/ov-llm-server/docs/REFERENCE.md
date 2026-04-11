# Reference

## API usage
Example request body:
```json
{
  "model": "qwen",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain what OpenVINO is in one sentence."}
  ],
  "tools": [],
  "stream": false,
  "temperature": 0.7
}
```

Example curl:
```bash
curl http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @docs/examples/request.json
```

Note: the server uses `OV_MODEL_PATH` as a fallback and echoes the `model` field back.
If a registry entry exists for the requested `model`, the server loads it instead.

## Conversion outputs
Each converted model gets a `conversion.json` in its output folder:
```json
{
  "name": "ov-qwen2-5-3b-instruct-fp16",
  "source_path": "/home/christopherbailey/model/Qwen2.5-3B-Instruct",
  "original_path": "/home/christopherbailey/model/og_models/Qwen2.5-3B-Instruct",
  "converted_path": "/home/christopherbailey/models/converted_models/ov-qwen2-5-3b-instruct-fp16/task-text-generation-with-past__wf-fp16",
  "task": "text-generation-with-past",
  "weight_format": "fp16",
  "converted_at": "2025-12-30T10:05:00+00:00"
}
```

The registry file lives at `~/models/converted_models/registry.json`:
```json
{
  "version": 1,
  "models": {
    "ov-qwen2-5-3b-instruct-fp16": {
      "path": "/home/christopherbailey/models/converted_models/ov-qwen2-5-3b-instruct-fp16/task-text-generation-with-past__wf-fp16",
      "task": "text-generation-with-past",
      "weight_format": "fp16"
    }
  }
}
```

## Warm-up commands
Preload one or more models into memory:
```bash
ov-warm-models ov-qwen2-5-3b-instruct-fp16 ov-llama-3-2-3b-instruct-fp16
```

Warm all models from the registry:
```bash
ov-warm-models
```

Custom server URL:
```bash
OV_SERVER_URL=http://localhost:9000 ov-warm-models
```

## Remote conversion via SSH
From another machine on your network:
```bash
ssh christopherbailey@192.168.1.71 "cd ~/ov-llm-server && ./scripts/ov-convert-model"
```

Override model root or output location:
```bash
ssh christopherbailey@192.168.1.71 "OV_MODEL_SRC=~/model OV_MODEL_OUT=~/models/converted_models cd ~/ov-llm-server && ./scripts/ov-convert-model"
```

## OpenVINO GenAI syntax (Python)
Critical: use `openvino_genai` (not `optimum-intel` or `openvino.runtime`).

```python
import openvino_genai as ov_genai

# Initialization (GPU)
pipe = ov_genai.LLMPipeline(
    "~/models/converted_models/<model>/task-text-generation-with-past__wf-fp16",
    "GPU",
)

# Generation config
config = ov_genai.GenerationConfig()
config.max_new_tokens = 1024
config.do_sample = True
config.temperature = 0.7

# Tokenization & chat template
# The pipeline handles tokenization, but for an API server we usually
# apply the template manually to get the prompt string first.

# Streaming inference (callback example)
def streamer_callback(subword: str) -> bool:
    print(subword, end="", flush=True)
    return False  # continue generation

pipe.generate(prompt, config, streamer_callback)
```

## Pydantic schemas (tools parameter)
```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class FunctionCall(BaseModel):
    name: str
    arguments: str  # JSON string

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: FunctionCall

class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    tools: Optional[List[Dict[str, Any]]] = None
    stream: bool = False
    temperature: float = 0.7
```
