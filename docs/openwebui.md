# Open WebUI (Mini) — Non-Docker Install

Open WebUI provides a local chat UI that talks to LiteLLM via OpenAI-compatible APIs. citeturn1search1

## Install Location (Mini)
- App dir: `/home/christopherbailey/open-webui`
- Data dir: `/home/christopherbailey/.open-webui`
- Env file: `/etc/open-webui/env`
- Systemd unit: `/etc/systemd/system/open-webui.service`

## Service (systemd)
```
systemctl status open-webui
sudo systemctl restart open-webui
```

## LiteLLM Upstream
Open WebUI uses OpenAI-compatible settings and plain model names from LiteLLM:
- `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`
- `OPENAI_API_KEY=dummy`

These environment variables are `PersistentConfig` in Open WebUI, so the app stores them after first start. citeturn0search0

## Install Notes
- The Open WebUI docs recommend Python 3.11 and describe `uv` / `pip`-based installs for non-Docker setups. citeturn1search1

## Access
Open WebUI listens on `http://<mini-host>:3000` by default.

## Resource Notes
- The UI service itself is CPU/RAM bound and does not use the Mini’s GPU.
- Inference is performed by LiteLLM backends (Studio MLX + Mini OpenVINO).
- If you enable Open WebUI features like embeddings or OCR, it will use more CPU/RAM and local storage.
