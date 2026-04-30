# Runbook: SearXNG

## Start/stop
```bash
sudo systemctl start searxng.service
sudo systemctl stop searxng.service
sudo systemctl restart searxng.service
```

## Logs
```bash
journalctl -u searxng.service -f
```

## Health
```bash
curl http://127.0.0.1:8888
```

## Engine curation
The current Mini runtime uses `/etc/searxng/settings.yml` overrides to keep the
engine mix small and predictable for Open WebUI web search. When search quality
regresses:

```bash
sudo journalctl -u searxng.service -n 200 --no-pager | rg 'HTTP error 403|suspended_time'
sudo sed -n '1,260p' /etc/searxng/settings.yml
```

If an engine is repeatedly suspended or obviously noisy, disable it explicitly
in `/etc/searxng/settings.yml`, then restart and re-smoke:

```bash
curl -fsS "http://127.0.0.1:8888/search?q=openwebui+searxng&format=json" \
  | jq '{count:(.results|length), first:(.results[0] // {}) | {title, url}}'
```
