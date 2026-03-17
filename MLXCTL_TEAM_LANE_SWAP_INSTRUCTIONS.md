# Studio Team Lanes via `mlxctl`

This is the current, validated operator guidance for the Studio team lanes.

Current validated state:
- `main` on `8101`: `mlx-community/Llama-3.3-70B-Instruct-4bit`
- `fast` on `8102`: keep the last known-good model until a replacement passes direct tool-call validation

Important:
- Team lanes `8100-8119` are `mlxctl`-managed.
- Do not start/stop `vllm` or `mlx-openai-server` directly on Studio.
- Run the parity preflight first.
- Do not publish a new `fast` model through LiteLLM/OpenCode/Open WebUI unless it passes direct Studio tool probes.

## What Was Tried for `fast`

I tested `mlx-community/Seed-OSS-36B-Instruct-4bit` as the `fast` replacement on the current Studio `vllm-metal` runtime.

The render was updated to use the Seed-family flags that upstream documents:
- `--enable-auto-tool-choice`
- `--tool-call-parser seed_oss`
- `--trust-remote-code`
- `--chat-template <local chat_template.jinja>`

Sources:
- [vLLM tool calling docs](https://docs.vllm.ai/en/latest/features/tool_calling/)
- [vLLM Seed recipe](https://docs.vllm.ai/projects/recipes/en/latest/Seed/Seed-OSS-36B.html)
- [ByteDance Seed model card](https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Instruct)

Observed local result on Studio:
- the server boots
- `/v1/models` responds
- tool calling is not reliable enough for OpenCode/MCP use

Direct repeated probes against `8102` produced all of these outcomes:
- correct `tool_calls` with function name `noop`
- no `tool_calls` at all and `finish_reason="length"`
- incorrect tool names like `example_function_name` or `function_name`

That means `Seed-OSS-36B` is **not currently validated for production use on `fast`** in this runtime, even after applying the family-appropriate `vllm` flags.

## Safe Current Procedure

If you need to keep the team lanes healthy today:
- keep `main` on Llama 3.3 with tool use enabled
- keep `fast` on its last known-good model until another candidate passes direct lane validation

## 1. Parity Preflight from the Repo Host

```bash
cd /home/christopherbailey/homelab-llm
./platform/ops/scripts/mlxctl studio-cli-sha || ./platform/ops/scripts/mlxctl sync-studio-cli
```

## 2. Disk Check Before Large Downloads

```bash
ssh studio 'df -h /Users/thestudio /Users/thestudio/models'
```

## 3. SSH into Studio and Set Only the Repo Vars

For the validated `main` lane:

```bash
ssh studio

export MAIN_REPO='mlx-community/Llama-3.3-70B-Instruct-4bit'
export FAST_REPO='mlx-community/gpt-oss-20b-MXFP4-Q4'
```

You can manage `HF_TOKEN` yourself if needed.

## 4. Studio Preflight

```bash
mlxctl --local status --checks --json
mlxctl --local vllm-capabilities --json
```

## 5. Ensure the Repos Are Registered

```bash
mlxctl --local ensure "$MAIN_REPO" --convert auto --preconverted auto --no-sync
mlxctl --local ensure "$FAST_REPO" --convert auto --preconverted auto --no-sync
```

## 6. Normalize the `main` Lane Settings

`main` is validated with Llama-family tool calling:

```bash
mlxctl --local vllm-set "$MAIN_REPO" --clear-vllm
mlxctl --local vllm-set "$MAIN_REPO" \
  --profile llama3_json \
  --tool-choice-mode auto \
  --max-model-len 65536 \
  --memory-fraction auto \
  --no-async-scheduling
```

The effective parser comes from the runtime profile:
- `tool_call_parser=llama3_json`
- no reasoning parser by default

Sources:
- [vLLM tool calling docs](https://docs.vllm.ai/en/latest/features/tool_calling/)
- [Meta Llama 3.3 docs](https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_3/)

## 7. Load `main` Only If Needed

Check the current `8101` target:

```bash
mlxctl --local status --checks --json | jq '.ports[] | select(.port==8101) | .actual_serving_target.repo_id'
```

If it is not already `mlx-community/Llama-3.3-70B-Instruct-4bit`, load it:

```bash
mlxctl --local load "$MAIN_REPO" 8101 --force --no-sync
```

## 8. Validate `main` Directly on Studio

```bash
mlxctl --local status --checks --json | jq '.ports[] | select(.port==8101)'
curl -fsS http://127.0.0.1:8101/v1/models | jq .
mlxctl --local vllm-render --ports 8101 --validate --json
```

Success means:
- `health_state` is `serving`
- `reconciliation_state` is `converged`
- `/v1/models` responds

## 9. Direct Tool Probe for `main`

```bash
export MAIN_SERVED_MODEL="$(curl -fsS http://127.0.0.1:8101/v1/models | jq -r '.data[0].id')"

python3 - <<'PY'
import json, os, urllib.request
payload = {
    "model": os.environ["MAIN_SERVED_MODEL"],
    "messages": [{"role": "user", "content": "Use the noop tool once, then stop."}],
    "tools": [{
        "type": "function",
        "function": {
            "name": "noop",
            "description": "noop",
            "parameters": {"type": "object", "properties": {}}
        }
    }],
    "tool_choice": "auto",
    "stream": False,
    "max_tokens": 128
}
req = urllib.request.Request(
    "http://127.0.0.1:8101/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    body = json.loads(resp.read().decode())
print(json.dumps(body["choices"][0]["message"], indent=2))
PY
```

`main` is acceptable when:
- `tool_calls` is present
- the function name is `noop`
- the response is not just raw parser markup

## 10. Sync the Gateway and Restart LiteLLM Only After Direct Validation

```bash
mlxctl --local sync-gateway
ssh mini 'sudo systemctl restart litellm-orch.service'
```

Then verify:

```bash
ssh mini 'systemctl status litellm-orch.service --no-pager'
ssh mini 'journalctl -u litellm-orch.service -n 80 --no-pager'
```

## 11. LiteLLM Alias Validation

List aliases:

```bash
ssh mini 'bash -lc "
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
curl -fsS -H \"Authorization: Bearer ${LITELLM_MASTER_KEY}\" \
  http://127.0.0.1:4000/v1/models | jq -r \".data[].id\" | sort
"'
```

Tool probe for `main` through LiteLLM:

```bash
ssh mini 'bash -lc "
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
python3 - <<\"PY\"
import json, os, urllib.request
payload={
  \"model\":\"main\",
  \"messages\":[{\"role\":\"user\",\"content\":\"Use the noop tool once, then stop.\"}],
  \"tools\":[{\"type\":\"function\",\"function\":{\"name\":\"noop\",\"description\":\"noop\",\"parameters\":{\"type\":\"object\",\"properties\":{}}}}],
  \"tool_choice\":\"auto\",
  \"stream\":False,
  \"max_tokens\":128
}
req=urllib.request.Request(
  \"http://127.0.0.1:4000/v1/chat/completions\",
  data=json.dumps(payload).encode(),
  headers={\"Authorization\": f\"Bearer {os.environ['LITELLM_MASTER_KEY']}\", \"Content-Type\":\"application/json\"},
  method=\"POST\"
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body[\"choices\"][0][\"message\"], indent=2))
PY
"'
```

## 12. OpenCode and Open WebUI Validation

Only do this after the direct lane and LiteLLM tool probes are correct.

OpenCode:

```bash
opencode models litellm
opencode run -m litellm/main "Reply with exactly: main-ok"
```

Open WebUI:

Use the existing authenticated API path or a manual authenticated session against `main`. Do not treat Open WebUI as validated if the backend lane has not already passed the direct and LiteLLM tool probes.

## Canary-Only `Seed-OSS-36B` Procedure

This section is **not production-validated** on the current runtime. Use it only if you want to reproduce the failed canary.

```bash
ssh studio

export FAST_REPO='mlx-community/Seed-OSS-36B-Instruct-4bit'

mlxctl --local ensure "$FAST_REPO" --convert auto --preconverted auto --no-sync

mlxctl --local vllm-set "$FAST_REPO" --clear-vllm
mlxctl --local vllm-set "$FAST_REPO" \
  --profile seed_oss \
  --tool-choice-mode auto \
  --max-model-len 65536 \
  --memory-fraction auto \
  --no-async-scheduling

mlxctl --local load "$FAST_REPO" 8102 --force --no-sync
mlxctl --local vllm-render --ports 8102 --validate --json
```

Expected current render:
- `--enable-auto-tool-choice`
- `--tool-call-parser seed_oss`
- `--trust-remote-code`
- `--chat-template <snapshot>/chat_template.jinja`

Do not sync this to LiteLLM unless repeated direct tool probes show the function name `noop` reliably.

## Rollback `fast` to the Last Known-Good GPT-OSS Target

If a `fast` canary fails, restore it:

```bash
ssh studio

export FAST_REPO='mlx-community/gpt-oss-20b-MXFP4-Q4'

mlxctl --local ensure "$FAST_REPO" --convert auto --preconverted auto --no-sync
mlxctl --local vllm-set "$FAST_REPO" --clear-vllm
mlxctl --local load "$FAST_REPO" 8102 --force --no-sync
mlxctl --local status --checks --json | jq '.ports[] | select(.port==8102)'
curl -fsS http://127.0.0.1:8102/v1/models | jq .
```

If the gateway had already been synced to the failed canary:

```bash
mlxctl --local sync-gateway
ssh mini 'sudo systemctl restart litellm-orch.service'
```

## Bottom Line

On the current Studio runtime:
- `main` on Llama 3.3 is validated for tool use
- `Seed-OSS-36B` is not yet validated as a `fast` replacement for OpenCode/MCP workflows
- do not publish a new `fast` alias until the raw `8102` lane passes repeated tool probes cleanly
