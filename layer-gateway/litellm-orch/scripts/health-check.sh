#!/usr/bin/env bash
set -euo pipefail

# Health checks for upstream backends.
# Usage: scripts/health-check.sh
# Default: readiness check (fast, no deep backend probes).
# Set VERBOSE=1 to hit /health (deep checks).

BASE_URL="${BASE_URL:-http://localhost:4000}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_LOCAL="${LITELLM_ENV_LOCAL:-$REPO_ROOT/layer-gateway/litellm-orch/config/env.local}"
LITELLM_API_KEY="${LITELLM_API_KEY:-}"

if [[ -z "${LITELLM_API_KEY}" && -f "$ENV_LOCAL" ]]; then
  LITELLM_API_KEY="$(grep -E '^LITELLM_MASTER_KEY=' "$ENV_LOCAL" | tail -n1 | cut -d= -f2-)"
fi

if [[ -z "${LITELLM_API_KEY}" ]]; then
  echo "missing LITELLM_API_KEY (set env or update ${ENV_LOCAL})" >&2
  exit 1
fi
VERBOSE="${VERBOSE:-0}"

if [[ "${VERBOSE:-0}" == "1" ]]; then
  raw="$(curl -fsS -H "Authorization: Bearer ${LITELLM_API_KEY}" "${BASE_URL}/health")"
else
  raw="$(curl -fsS -H "Authorization: Bearer ${LITELLM_API_KEY}" "${BASE_URL}/health/readiness")"
fi

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
