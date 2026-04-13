# Voice Gateway Demo

This is the quickest operator-safe demo for the current Orin speech appliance.

Canonical path:

`Open WebUI -> LiteLLM -> voice-gateway -> Speaches`

This demo is intentionally direct to `voice-gateway` for isolated validation.

## Preconditions
- Run on the Orin host (`ssh orin`)
- `voice-gateway.service` is active
- `VOICE_GATEWAY_API_KEY` is available from `/etc/voice-gateway/voice-gateway.env`

## 1) Health and model surface
```bash
api_key="$(sudo awk -F= '$1=="VOICE_GATEWAY_API_KEY" {print substr($0, index($0, "=")+1)}' /etc/voice-gateway/voice-gateway.env)"

curl -fsS http://192.168.1.93:18080/health
curl -fsS http://192.168.1.93:18080/health/readiness | jq .
curl -fsS http://192.168.1.93:18080/v1/models -H "Authorization: Bearer ${api_key}" | jq .
curl -fsS http://192.168.1.93:18080/v1/speakers -H "Authorization: Bearer ${api_key}" | jq .
```

## 2) Generate one TTS canary
```bash
curl -fsS http://192.168.1.93:18080/v1/audio/speech \
  -H "Authorization: Bearer ${api_key}" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"Homelab speech demo.","voice":"alloy","response_format":"wav","speed":1.0}' \
  --output /tmp/voice-gateway-demo.wav
```

## 3) Optional playback on Orin
```bash
paplay /tmp/voice-gateway-demo.wav
```

If `paplay` is unavailable:
```bash
aplay -D plughw:CARD=Mini,DEV=0 /tmp/voice-gateway-demo.wav
```

## 4) Optional control-plane checks
```bash
PYTHONPATH=/home/christopherbailey/voice-gateway-canary/src \
  python3 -m voice_gateway.ops_cli --base-url http://192.168.1.93:18080 --api-key "${api_key}" status

PYTHONPATH=/home/christopherbailey/voice-gateway-canary/src \
  python3 -m voice_gateway.ops_cli registry-list | jq '.count? // (.models | length)'
```

Notes:
- This demo validates the current service contract only.
- Historical XTTS wrapper-proof flows are intentionally out of the active operator path.
