# Runbook: youtube-transcript-api

## Install env
```bash
sudo install -d -m 0755 /etc/homelab-llm
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/templates/youtube-transcript-api.env.example \
  /etc/homelab-llm/youtube-transcript-api.env
```

## Install service
```bash
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/systemd/youtube-transcript-api.service \
  /etc/systemd/system/youtube-transcript-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now youtube-transcript-api.service
```

## Logs
```bash
journalctl -u youtube-transcript-api.service -n 200 --no-pager
```

## Direct smoke
```bash
curl -fsS http://127.0.0.1:8014/health
curl -fsS http://127.0.0.1:8014/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"youtube-transcript","messages":[{"role":"user","content":"https://youtu.be/dQw4w9WgXcQ"}]}' | jq -r '.choices[0].message.content'
```

## LiteLLM smoke
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{"model":"task-youtube-transcript","messages":[{"role":"user","content":"https://youtu.be/dQw4w9WgXcQ"}]}' | jq -r '.choices[0].message.content'
```
