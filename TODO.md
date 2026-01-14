# Studio launchd update (requires sudo on Studio)

Status: legacy notes for a GPT-OSS launchd setup on port 8100. Current MLX
port management is handled via `platform/ops/scripts/mlxctl` and the registry. Use this
only if you intentionally revert to a single fixed launchd model on 8100.

Goal: run `jerry-chat` (GPT-OSS) at boot on port `8100` via `com.bebop.mlx-launch`.

## Edit `/opt/mlx-launch/bin/start.sh`
Replace the model line so it launches GPT-OSS:

```bash
MODEL_PATH="halley-ai/gpt-oss-120b-MLX-6bit-gs64"
```

Keep `PORT="8100"` as-is.

## Restart launchd service

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl kickstart -k system/com.bebop.mlx-launch
```

## Verify

```bash
sudo lsof -nP -iTCP:8100 -sTCP:LISTEN
sudo tail -n 200 /opt/mlx-launch/logs/launchd.out.log
sudo tail -n 200 /opt/mlx-launch/logs/launchd.err.log
```

## Debugging if launchd appears to do nothing

```bash
sudo launchctl print system/com.bebop.mlx-launch | rg -n "state|pid|last exit|exit code|program"
sudo tail -n 200 /opt/mlx-launch/logs/launchd.out.log
sudo tail -n 200 /opt/mlx-launch/logs/launchd.err.log
sudo tail -n 200 /opt/mlx-launch/logs/server.log
sudo tail -n 200 /opt/mlx-launch/logs/app.log
sudo -u thestudio /opt/mlx-launch/bin/start.sh
```

If the log is too verbose and the error is hidden, pull the error lines and a wider window:

```bash
sudo rg -n "ERROR|Exception|Traceback|Failed" /opt/mlx-launch/logs/server.log
sudo rg -n "ERROR|Exception|Traceback|Failed" /opt/mlx-launch/logs/app.log
sudo tail -n 500 /opt/mlx-launch/logs/server.log
```

## Force local snapshot (avoid re-downloads)

Use the local HF snapshot path instead of the repo ID:

```bash
MODEL_PATH="/Users/thestudio/models/hf/hub/models--halley-ai--gpt-oss-120b-MLX-6bit-gs64/snapshots/81d4949e4744e742a5fda5125ab6e0ccf2bf95c0"
```

Optional (only after confirming snapshot exists):

```bash
export HF_HUB_OFFLINE=1
```

Then restart launchd:

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl kickstart -k system/com.bebop.mlx-launch
```

## Prevent GPT-OSS from emitting internal "analysis" tokens

Create a GPT-OSS chat template and wire it into the launchd server:

```bash
sudo mkdir -p /Users/thestudio/models/chat_templates
sudo tee /Users/thestudio/models/chat_templates/gptoss.jinja >/dev/null <<'EOF'
{{- bos_token }}
{% for message in messages -%}
{% if message['role'] == 'system' -%}
<|system|>{{ message['content'] }}<|end|>
{% elif message['role'] == 'user' -%}
<|user|>{{ message['content'] }}<|end|>
{% elif message['role'] == 'assistant' -%}
<|assistant|>{{ message['content'] }}<|end|>
{% endif -%}  501  4159  4132   0  3:01AM ttys011    0:00.01 rg mlx-openai-server.*8100
thestudio@thestudio ~
{% endfor -%}
<|assistant|>
EOF
```

Edit `/opt/mlx-launch/bin/start.sh` and add:

```
--chat-template-file "/Users/thestudio/models/chat_templates/gptoss.jinja"
```

Restart launchd:

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl kickstart -k system/com.bebop.mlx-launch
```



## Fix GPT-OSS analysis leak by using model’s own chat_template (recommended)

Extract the template from the model’s tokenizer config and overwrite `gptoss.jinja`:

```bash
python3 - <<'PY'
import json, pathlib
model_dir = pathlib.Path("/Users/thestudio/models/hf/hub/models--halley-ai--gpt-oss-120b-MLX-6bit-gs64/snapshots/81d4949e4744e742a5fda5125ab6e0ccf2bf95c0")
cfg = json.loads((model_dir / "tokenizer_config.json").read_text())
tmpl = cfg.get("chat_template")
if not tmpl:
    raise SystemExit("No chat_template found in tokenizer_config.json")
out = pathlib.Path("/Users/thestudio/models/chat_templates/gptoss.jinja")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(tmpl)
print(f"Wrote {out}")
PY
```

Ensure `/opt/mlx-launch/bin/start.sh` includes:

```bash
MODEL_PATH="/Users/thestudio/models/hf/hub/models--halley-ai--gpt-oss-120b-MLX-6bit-gs64/snapshots/81d4949e4744e742a5fda5125ab6e0ccf2bf95c0"
--chat-template-file "/Users/thestudio/models/chat_templates/gptoss.jinja"
```

Restart launchd and test output:

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl kickstart -k system/com.bebop.mlx-launch

curl -sS http://127.0.0.1:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/Users/thestudio/models/hf/hub/models--halley-ai--gpt-oss-120b-MLX-6bit-gs64/snapshots/81d4949e4744e742a5fda5125ab6e0ccf2bf95c0","messages":[{"role":"user","content":"say hello and a short fact about foxes"}],"max_tokens":64}' \
  | jq .
```


## Fix common launchd script mistakes (chat template not applied)

If you see a running process without `--chat-template-file`, fix the `exec` block and restart launchd.

Use this exact block (note the space before `\`):

```bash
exec /opt/homebrew/bin/uv run mlx-openai-server launch \
  --host "$HOST" \
  --port "$PORT" \
  --model-path "$MODEL_PATH" \
  --model-type "$MODEL_TYPE" \
  --chat-template-file "/Users/thestudio/models/chat_templates/gptoss.jinja" \
  --log-file "/opt/mlx-launch/logs/app.log" \
  > /opt/mlx-launch/logs/server.log 2>&1
```

Then restart:

```bash
sudo lsof -ti -iTCP:8100 -sTCP:LISTEN | xargs sudo kill
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl kickstart -k system/com.bebop.mlx-launch
```

## Alternative fix: Open WebUI Harmony2Think filter (UI-side)

This strips Harmony `<|channel|>` tokens before display.

1) Open WebUI → Workspace → Functions → Import.
2) Import the Harmony2Think Filter from the Open WebUI community.
3) Workspace → Models → edit `jerry-chat` → Filters → enable Harmony2Think.
4) Save, then refresh models or restart Open WebUI.

## Alternative fix: MLX server Harmony parsers (backend-side)

If your MLX server supports it, add these flags to `/opt/mlx-launch/bin/start.sh`:

```bash
--reasoning-parser harmony
--tool-call-parser harmony
```

Then restart launchd and test:
```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl kickstart -k system/com.bebop.mlx-launch
```

## Preferred fix (MLX Harmony parsers)

Since your MLX server supports Harmony parsers, use these instead of a custom chat template.

1) Edit `/opt/mlx-launch/bin/start.sh`:
- Remove the chat template line:
  `--chat-template-file "/Users/thestudio/models/chat_templates/gptoss.jinja"`
- Add these flags:

```bash
--tool-call-parser harmony
--reasoning-parser harmony
```

2) Restart launchd:

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.mlx-launch.plist
sudo launchctl kickstart -k system/com.bebop.mlx-launch
```

3) Test output:

```bash
curl -sS http://127.0.0.1:8100/v1/chat/completions   -H "Content-Type: application/json"   -d '{"model":"/Users/thestudio/models/hf/hub/models--halley-ai--gpt-oss-120b-MLX-6bit-gs64/snapshots/81d4949e4744e742a5fda5125ab6e0ccf2bf95c0","messages":[{"role":"user","content":"say hello"}],"max_tokens":64}'   | jq .
```

## If a test model fails with “Missing parameters”

This usually means the model is not compatible with the MLX loader (not a download issue).

```bash
ls -la /Users/thestudio/models/hf/hub/models--mlx-community--Qwen3-235B-A22B-Instruct-2507-6bit/snapshots/6dd2ef235d39fb976237fd9243184741d8407a55 | head
rg -n "architectures|model_type" /Users/thestudio/models/hf/hub/models--mlx-community--Qwen3-235B-A22B-Instruct-2507-6bit/snapshots/6dd2ef235d39fb976237fd9243184741d8407a55/config.json
```
