#!/usr/bin/env bash
set -euo pipefail

# Operator smoke for the Mini/LiteLLM-fronted personal ASR route.
# Requires: curl, jq, python3

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_AUDIO_FILE="${REPO_ROOT}/tests/fixtures_personal_asr_whisperkit_smoke.wav"
MODEL="${ASR_SMOKE_MODEL:-personal-asr-whisperkit}"
BASE_URL="${BASE_URL:-${LITELLM_BASE_URL:-http://127.0.0.1:4000/v1}}"
AUDIO_FILE="${ASR_SMOKE_AUDIO:-$DEFAULT_AUDIO_FILE}"
EXPECTED_TEXT="${ASR_SMOKE_EXPECTED_TEXT:-Argmax WhisperKit local transcription health check}"
API_KEY="${PERSONAL_ASR_LITELLM_KEY:-${LITELLM_API_KEY:-}}"
MAX_BYTES="${ASR_SMOKE_MAX_BYTES:-10485760}"
MAX_DURATION_SECONDS="${ASR_SMOKE_MAX_DURATION_SECONDS:-30}"
CHECK_NEGATIVE_AUTH="${ASR_SMOKE_CHECK_NEGATIVE_AUTH:-1}"
CHECK_UNAUTHORIZED_MODEL="${ASR_SMOKE_CHECK_UNAUTHORIZED_MODEL:-1}"
UNAUTHORIZED_MODELS="${ASR_SMOKE_UNAUTHORIZED_MODELS:-${ASR_SMOKE_UNAUTHORIZED_MODEL:-fast voice-stt voice-stt-canary large-v3-v20240930_626MB}}"
CHECK_PROMPT_REJECTION="${ASR_SMOKE_CHECK_PROMPT_REJECTION:-1}"
CHECK_SILENT_REJECTION="${ASR_SMOKE_CHECK_SILENT_REJECTION:-1}"
CHECK_MALFORMED_REJECTION="${ASR_SMOKE_CHECK_MALFORMED_REJECTION:-1}"
CURL_CONNECT_TIMEOUT="${ASR_SMOKE_CURL_CONNECT_TIMEOUT:-5}"
CURL_MAX_TIME="${ASR_SMOKE_CURL_MAX_TIME:-120}"
MODEL_OPERATION_LABEL="${MODEL//[^A-Za-z0-9_]/_}"
OPERATION_ID="${HOMELAB_OPERATION_ID:-op_$(date -u +%Y%m%dT%H%M%SZ)_${MODEL_OPERATION_LABEL}_smoke}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

require_cmd curl
require_cmd jq
require_cmd python3

if [[ -z "$API_KEY" ]]; then
  echo "missing PERSONAL_ASR_LITELLM_KEY or LITELLM_API_KEY" >&2
  exit 1
fi

if [[ -z "${EXPECTED_TEXT//[[:space:]]/}" ]]; then
  echo "ASR_SMOKE_EXPECTED_TEXT must be non-empty" >&2
  exit 1
fi

if [[ ! -f "$AUDIO_FILE" ]]; then
  echo "missing ASR smoke audio fixture: $AUDIO_FILE" >&2
  exit 1
fi

bytes="$(wc -c <"$AUDIO_FILE" | tr -d ' ')"
if [[ "$bytes" -le 0 || "$bytes" -gt "$MAX_BYTES" ]]; then
  echo "audio fixture size out of bounds: ${bytes} bytes" >&2
  exit 1
fi

python3 - "$AUDIO_FILE" "$MAX_DURATION_SECONDS" <<'PY'
import sys
import wave

path = sys.argv[1]
max_duration = float(sys.argv[2])
try:
    with wave.open(path, "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        channels = wav.getnchannels()
        duration = frames / rate if rate else 0.0
except (EOFError, wave.Error, OSError) as exc:
    raise SystemExit(f"audio fixture is not a readable WAV file: {exc}")

if duration <= 0 or duration > max_duration:
    raise SystemExit(f"audio fixture duration out of bounds: {duration:.3f}s")
if channels < 1:
    raise SystemExit("audio fixture has no channels")
print(f"fixture: wav {channels}ch {rate}Hz {duration:.3f}s")
PY

hex_bytes() {
  od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'
}

TRACEPARENT="${TRACEPARENT:-00-$(hex_bytes 16)-$(hex_bytes 8)-01}"
endpoint="${BASE_URL%/}/audio/transcriptions"

tmp_body="$(mktemp)"
tmp_err="$(mktemp)"
cleanup_paths=("$tmp_body" "$tmp_err")
cleanup() {
  rm -f "${cleanup_paths[@]}"
}
trap cleanup EXIT

post_transcription() {
  local key="$1"
  local model="$2"
  local audio="$3"
  local body="$4"
  shift 4
  local headers=(-H "traceparent: ${TRACEPARENT}" -H "x-homelab-operation-id: ${OPERATION_ID}")
  if [[ -n "$key" ]]; then
    headers+=(-H "Authorization: Bearer ${key}")
  fi
  curl -sS -o "$body" -w '%{http_code}' \
    --connect-timeout "$CURL_CONNECT_TIMEOUT" \
    --max-time "$CURL_MAX_TIME" \
    "${headers[@]}" \
    -F "model=${model}" \
    -F "file=@${audio}" \
    -F "language=en" \
    -F "response_format=json" \
    "$@" \
    "$endpoint" 2>"$tmp_err"
}

redacted_curl_error() {
  if [[ -s "$tmp_err" ]]; then
    sed -E 's/(Authorization: Bearer )[[:graph:]]+/\1[REDACTED]/g; s/(sk-[[:alnum:]_-]{6})[[:alnum:]_-]+/\1...[REDACTED]/g' "$tmp_err" >&2
  fi
}

run_post_transcription() {
  local label="$1"
  shift
  local status
  if ! status="$(post_transcription "$@")"; then
    echo "${label}: curl failed" >&2
    redacted_curl_error
    exit 1
  fi
  printf '%s' "$status"
}

expect_failure_status() {
  local label="$1"
  local status="$2"
  local expected="$3"
  local expected_label="$4"
  if [[ ! "$status" =~ $expected ]]; then
    echo "${label} expected ${expected_label}, got HTTP ${status}" >&2
    exit 1
  fi
  echo "${label}: rejected with HTTP ${status}"
}

status="$(run_post_transcription "happy-path" "$API_KEY" "$MODEL" "$AUDIO_FILE" "$tmp_body")"
if [[ ! "$status" =~ ^2 ]]; then
  echo "ASR smoke failed with HTTP ${status}" >&2
  jq -c '{error:(.error // .detail // .message // "unknown")}' "$tmp_body" >&2 || true
  exit 1
fi

text="$(jq -er '(.text // .output_text // "") | strings' "$tmp_body")" || {
  echo "ASR smoke response is not parseable JSON transcription text" >&2
  exit 1
}

if [[ -z "${text//[[:space:]]/}" ]]; then
  echo "ASR smoke returned empty transcript text" >&2
  exit 1
fi

TEXT="$text" EXPECTED="$EXPECTED_TEXT" python3 - <<'PY'
import os
import re
import sys

def norm(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()

actual = norm(os.environ["TEXT"])
expected = norm(os.environ["EXPECTED"])
if expected and expected not in actual:
    raise SystemExit("ASR smoke transcript did not contain expected text")
print(f"happy-path: matched expected text; transcript_chars={len(os.environ['TEXT'])}")
PY

if [[ "$CHECK_NEGATIVE_AUTH" == "1" ]]; then
  status="$(run_post_transcription "missing-auth" "" "$MODEL" "$AUDIO_FILE" "$tmp_body")"
  expect_failure_status "missing-auth" "$status" '^401$' "HTTP 401"
  status="$(run_post_transcription "invalid-auth" "invalid-personal-asr-smoke" "$MODEL" "$AUDIO_FILE" "$tmp_body")"
  expect_failure_status "invalid-auth" "$status" '^401$' "HTTP 401"
fi

if [[ "$CHECK_UNAUTHORIZED_MODEL" == "1" ]]; then
  for unauthorized_model in $UNAUTHORIZED_MODELS; do
    status="$(run_post_transcription "unauthorized-model:${unauthorized_model}" "$API_KEY" "$unauthorized_model" "$AUDIO_FILE" "$tmp_body")"
    expect_failure_status "unauthorized-model:${unauthorized_model}" "$status" '^(401|403)$' "HTTP 401 or 403"
  done
fi

if [[ "$CHECK_PROMPT_REJECTION" == "1" ]]; then
  status="$(run_post_transcription "unsupported-prompt" "$API_KEY" "$MODEL" "$AUDIO_FILE" "$tmp_body" -F "prompt=not-supported")"
  expect_failure_status "unsupported-prompt" "$status" '^400$' "HTTP 400"
fi

if [[ "$CHECK_SILENT_REJECTION" == "1" ]]; then
  silent_wav="$(mktemp --suffix=.wav "${TMPDIR:-/tmp}/personal-asr-whisperkit-silent.XXXXXX")"
  cleanup_paths+=("$silent_wav")
  python3 - "$silent_wav" <<'PY'
import sys
import wave

with wave.open(sys.argv[1], "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(16000)
    wav.writeframes(b"\x00\x00" * 16000)
PY
  status="$(run_post_transcription "silent-input" "$API_KEY" "$MODEL" "$silent_wav" "$tmp_body")"
  expect_failure_status "silent-input" "$status" '^400$' "HTTP 400"
fi

if [[ "$CHECK_MALFORMED_REJECTION" == "1" ]]; then
  malformed_audio="$(mktemp --suffix=.wav "${TMPDIR:-/tmp}/personal-asr-whisperkit-malformed.XXXXXX")"
  cleanup_paths+=("$malformed_audio")
  printf 'not a wav file\n' >"$malformed_audio"
  status="$(run_post_transcription "malformed-audio" "$API_KEY" "$MODEL" "$malformed_audio" "$tmp_body")"
  expect_failure_status "malformed-audio" "$status" '^500$' "HTTP 500"
fi

echo "${MODEL} smoke passed"
echo "operation_id=${OPERATION_ID}"
echo "traceparent=${TRACEPARENT}"
