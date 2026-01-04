#!/usr/bin/env bash
set -euo pipefail

# Health checks for upstream backends.
# Usage: scripts/health-check.sh

BASE_URL="${BASE_URL:-http://localhost:4000}"
VERBOSE="${VERBOSE:-0}"

raw="$(curl -fsS "${BASE_URL}/health")"

if [[ "${VERBOSE}" == "1" ]]; then
  python3 - <<'PY' "$raw"
import json,sys
print(json.dumps(json.loads(sys.argv[1]), indent=2))
PY
  exit 0
fi

python3 - <<'PY' "$raw"
import json,sys,datetime

data = json.loads(sys.argv[1])
now = datetime.datetime.utcnow().isoformat() + "Z"

def compact(items, status):
  out = []
  for item in items:
    entry = {
      "model": item.get("model"),
      "api_base": item.get("api_base"),
      "status": status,
      "last_checked_at": now,
    }
    # Optional fields if present
    for key in ("latency_ms","error","capabilities","tags","provider","context_window","max_output_tokens","availability"):
      if key in item:
        entry[key] = item[key]
    out.append(entry)
  return out

healthy = compact(data.get("healthy_endpoints", []), "healthy")
unhealthy = compact(data.get("unhealthy_endpoints", []), "unhealthy")

out = {
  "healthy_count": data.get("healthy_count", len(healthy)),
  "unhealthy_count": data.get("unhealthy_count", len(unhealthy)),
  "checks": healthy + unhealthy,
}
print(json.dumps(out, indent=2))
PY
