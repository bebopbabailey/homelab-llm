# Registry Format

The model registry is stored outside the repo at:
`~/models/converted_models/registry.json`

## Schema
The file is JSON with a version and a models map:
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

## Notes
- Keys under `models` are canonical model IDs and must match the folder names
  under `~/models/converted_models/`.
- `path` points to the converted OpenVINO model directory.
- Extra metadata can be added later without breaking the format.
