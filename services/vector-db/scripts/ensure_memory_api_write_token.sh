#!/usr/bin/env bash
set -Eeuo pipefail

TOKEN_PATH="${MEMORY_API_WRITE_BEARER_TOKEN_FILE:-/Users/thestudio/data/memory-main/secrets/memory-api-write-token}"
mkdir -p "$(dirname "$TOKEN_PATH")"

if [[ ! -s "$TOKEN_PATH" ]]; then
  python3 - <<'PY' > "$TOKEN_PATH"
import secrets
print(secrets.token_urlsafe(32))
PY
  chmod 600 "$TOKEN_PATH"
fi

python3 - <<PY
import json, pathlib
path = pathlib.Path("${TOKEN_PATH}")
print(json.dumps({"ok": True, "token_path": str(path), "size": path.stat().st_size}, indent=2))
PY
