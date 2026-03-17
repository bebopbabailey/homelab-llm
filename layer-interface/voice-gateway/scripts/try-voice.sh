#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:18080"
OUTPUT_ROOT="/srv/ssd/outputs/voice-gateway"
PREFERRED_SINK="alsa_output.usb-Kiwi_Ears_Kiwi_Ears-Allegro_Mini_2020-02-20-0000-0000-0000-00.analog-stereo"

TEXT=""
VOICE=""
OUT=""
PLAY=1
LIST_ONLY=0
CYCLE=0
DEVICE=""

usage() {
  cat <<'EOF'
Usage:
  try-voice.sh --list
  try-voice.sh [--text "Hello"] [--voice default] [--out /path/file.wav] [--no-play]
  try-voice.sh --cycle [--text "Hello"]

Options:
  --list            List available voices and exit
  --cycle           Cycle through available preset voices one by one
  --text TEXT       Text to synthesize
  --voice VOICE     Voice id to use (defaults to "default")
  --out PATH        Output wav path
  --no-play         Do not play the result
  --device NAME     Explicit Pulse sink name for paplay
  --url URL         Override backend base URL (default: http://127.0.0.1:18080)
  --help            Show this help
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

check_backend() {
  local code
  local attempt
  for attempt in 1 2 3 4 5 6; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}/health" || true)"
    if [[ "$code" == "200" ]]; then
      return 0
    fi
    sleep 2
  done
  die "voice-gateway is not healthy at ${BASE_URL}. Start the local wrapper first."
}

safe_voice() {
  printf '%s' "$1" | tr '[:space:]/:' '---' | tr -cd '[:alnum:]_.-'
}

pick_output_root() {
  if [[ -d "$OUTPUT_ROOT" && -w "$OUTPUT_ROOT" ]]; then
    printf '%s\n' "$OUTPUT_ROOT"
    return 0
  fi

  local fallback="${TMPDIR:-/tmp}/voice-gateway"
  mkdir -p "$fallback"
  printf '%s\n' "$fallback"
}

fetch_speakers_json() {
  local tmp
  tmp="$(mktemp)"
  curl -m 180 -fsS "${BASE_URL}/v1/speakers" -o "$tmp"
  printf '%s\n' "$tmp"
}

list_voices() {
  local tmp="$1"
  python3 - "$tmp" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"Default voice: {payload.get('default_voice')}")
print("")
print("Voice IDs:")
for item in payload.get("voices", []):
    voice_id = item.get("id")
    backend = item.get("backend_speaker")
    active = item.get("active")
    available = item.get("available")
    print(f"  - {voice_id} (backend={backend}, active={active}, available={available})")
print("")
print("Discovered built-in speakers:")
for speaker in payload.get("discovered_builtin_speakers", []):
    print(f"  - {speaker}")
PY
}

request_speech() {
  local text="$1"
  local voice="$2"
  local out="$3"
  local body payload_file curl_meta http_code content_type

  body="$(mktemp)"
  payload_file="$(mktemp)"

  python3 - "$text" "$voice" >"$payload_file" <<'PY'
import json
import sys

payload = {
    "model": "xtts-v2",
    "input": sys.argv[1],
    "voice": sys.argv[2],
    "response_format": "wav",
    "language": "en",
}
print(json.dumps(payload))
PY

  curl_meta="$(
    curl -m 180 -sS \
      -o "$body" \
      -w '%{http_code}\n%{content_type}' \
      -H 'Content-Type: application/json' \
      --data-binary @"$payload_file" \
      "${BASE_URL}/v1/audio/speech"
  )"
  rm -f "$payload_file"

  http_code="$(printf '%s\n' "$curl_meta" | sed -n '1p')"
  content_type="$(printf '%s\n' "$curl_meta" | sed -n '2p' | tr -d '\r')"

  if [[ "$http_code" != "200" ]]; then
    printf 'backend returned HTTP %s\n' "$http_code" >&2
    python3 - "$body" <<'PY' || cat "$body" >&2
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
try:
    payload = json.loads(text)
except json.JSONDecodeError:
    print(text)
else:
    print(json.dumps(payload, indent=2, sort_keys=True))
PY
    rm -f "$body"
    return 1
  fi

  case "$content_type" in
    audio/wav*|audio/x-wav*)
      ;;
    *)
      printf 'unexpected content-type: %s\n' "$content_type" >&2
      python3 - "$body" <<'PY' || cat "$body" >&2
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
try:
    payload = json.loads(text)
except json.JSONDecodeError:
    print(text)
else:
    print(json.dumps(payload, indent=2, sort_keys=True))
PY
      rm -f "$body"
      return 1
      ;;
  esac

  mv "$body" "$out"
}

play_file() {
  local path="$1"
  local sink="${DEVICE}"
  if [[ -z "$sink" ]] && command -v pactl >/dev/null 2>&1; then
    if pactl list short sinks | awk '{print $2}' | grep -Fxq "$PREFERRED_SINK"; then
      sink="$PREFERRED_SINK"
    fi
  fi

  if command -v paplay >/dev/null 2>&1; then
    if [[ -n "$sink" ]]; then
      paplay --device="$sink" "$path"
    else
      paplay "$path"
    fi
    return 0
  fi

  if command -v aplay >/dev/null 2>&1; then
    aplay "$path"
    return 0
  fi

  die "no playback command available (need paplay or aplay)"
}

cycle_voices() {
  local tmp="$1"
  local output_dir output_path choice

  output_dir="$(pick_output_root)/voice-cycle-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$output_dir"

  python3 - "$tmp" <<'PY' >"${output_dir}/voices.txt"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
voice_ids = [item.get("id") for item in payload.get("voices", []) if item.get("id")]
seen = set()
for voice in voice_ids:
    if voice not in seen:
        print(voice)
        seen.add(voice)
for speaker in payload.get("discovered_builtin_speakers", []):
    if isinstance(speaker, str) and speaker and speaker not in seen:
        print(speaker)
        seen.add(speaker)
PY

  [[ -s "${output_dir}/voices.txt" ]] || die "no voices available to cycle"

  while IFS= read -r voice_name; do
    [[ -n "$voice_name" ]] || continue
    output_path="${output_dir}/voice-demo-$(safe_voice "$voice_name").wav"
    printf '\n=== voice: %s ===\n' "$voice_name"
    request_speech "$TEXT" "$voice_name" "$output_path"
    printf 'saved: %s\n' "$output_path"
    if [[ "$PLAY" -eq 1 ]]; then
      play_file "$output_path"
    fi
    read -r -p "Enter for next voice, q to stop: " choice
    if [[ "${choice:-}" == "q" || "${choice:-}" == "Q" ]]; then
      break
    fi
  done <"${output_dir}/voices.txt"

  printf '\ncycle output dir: %s\n' "$output_dir"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)
      LIST_ONLY=1
      shift
      ;;
    --cycle)
      CYCLE=1
      shift
      ;;
    --text)
      TEXT="${2:-}"
      shift 2
      ;;
    --voice)
      VOICE="${2:-}"
      shift 2
      ;;
    --out)
      OUT="${2:-}"
      shift 2
      ;;
    --no-play)
      PLAY=0
      shift
      ;;
    --device)
      DEVICE="${2:-}"
      shift 2
      ;;
    --url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

require_cmd curl
require_cmd python3
check_backend

speakers_json="$(fetch_speakers_json)"
trap 'rm -f "${speakers_json:-}"' EXIT

if [[ "$LIST_ONLY" -eq 1 ]]; then
  list_voices "$speakers_json"
  exit 0
fi

if [[ -z "$TEXT" ]]; then
  read -r -p "Enter text: " TEXT
fi

[[ -n "$TEXT" ]] || die "text cannot be empty"

if [[ "$CYCLE" -eq 1 ]]; then
  cycle_voices "$speakers_json"
  exit 0
fi

if [[ -z "$VOICE" ]]; then
  read -r -p "Voice [default]: " VOICE
fi
VOICE="${VOICE:-default}"

if [[ -z "$OUT" ]]; then
  OUTPUT_ROOT="$(pick_output_root)"
  OUT="${OUTPUT_ROOT}/voice-demo-$(safe_voice "$VOICE")-$(date +%Y%m%d-%H%M%S).wav"
else
  mkdir -p "$(dirname "$OUT")"
fi

request_speech "$TEXT" "$VOICE" "$OUT"

printf 'saved: %s\n' "$OUT"
printf 'voice: %s\n' "$VOICE"

if [[ "$PLAY" -eq 1 ]]; then
  play_file "$OUT"
  printf 'played: yes\n'
else
  printf 'played: no\n'
fi
