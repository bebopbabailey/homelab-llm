# Known Issues

## MLX server chat template + BatchEncoding error
**Symptom:** `Failed to generate text response: Invalid type transformers.tokenization_utils_base.BatchEncoding received in array initialization.`  
This occurs when the MLX OpenAI server calls `tokenizer.apply_chat_template(...)` and receives a `BatchEncoding` object instead of a list of token IDs. The server then passes that object into generation and crashes. The `mlx-lm` docs show `apply_chat_template` usage, but the return type can vary by tokenizer/model. citeturn0search1

**Why this happens:** Some models (including community conversions) rely on chat templates that are not consistently handled across tokenizers/servers. There are multiple upstream reports of chat-template-related failures in MLX tooling, which suggests this class of issue can recur across models. citeturn0search2turn0search3

**Recommended fix order:**
1) Launch MLX servers with `--trust-remote-code` and `--chat-template-file` to ensure the correct template is used.
2) If the error persists, apply a small local patch in the MLX server environment to coerce `BatchEncoding` to `input_ids` before generation.

**Local patch (current workaround on Studio):**  
We patched the MLX server’s venv to convert `BatchEncoding` → `input_ids` at the point where `apply_chat_template` returns the prompt tokens. This is a local environment change (e.g., in `/opt/mlx-launch/.venv/...`) and must be re-applied after MLX server upgrades. Keep the patch documented and repeatable.
