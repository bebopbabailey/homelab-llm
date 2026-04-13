#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PATCH_DIR="$REPO_ROOT/experiments/legacy/optillm-local/runtime/patches/mlx_lm"

DEFAULT_REF="ad067ea627c752bddaa194a4e4e8adc858a62433"
WORKSPACE="${WORKSPACE:-$HOME/optillm-mlx-experimental/mlx-lm-optillm}"
REF="${REF:-$DEFAULT_REF}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--workspace PATH] [--ref GIT_REF]

Creates an isolated mlx-lm workspace and applies the OptiLLM decode-time patch.

Options:
  --workspace PATH   Target workspace directory
  --ref GIT_REF      Upstream mlx-lm git ref (default: $DEFAULT_REF)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      WORKSPACE="$2"
      shift 2
      ;;
    --ref)
      REF="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$WORKSPACE")"

if [[ -d "$WORKSPACE/.git" ]]; then
  echo "[info] Using existing repo at $WORKSPACE"
  git -C "$WORKSPACE" fetch --tags origin
else
  echo "[info] Cloning mlx-lm into $WORKSPACE"
  git clone https://github.com/ml-explore/mlx-lm.git "$WORKSPACE"
fi

git -C "$WORKSPACE" checkout "$REF"

if ! git -C "$WORKSPACE" rev-parse --verify optillm-mlx-exp >/dev/null 2>&1; then
  git -C "$WORKSPACE" checkout -b optillm-mlx-exp
else
  git -C "$WORKSPACE" checkout optillm-mlx-exp
fi

cp "$PATCH_DIR/optillm_decoding.py" "$WORKSPACE/mlx_lm/optillm_decoding.py"

if rg -q "enable-optillm-decoding" "$WORKSPACE/mlx_lm/server.py"; then
  echo "[info] server.py already appears patched; skipping git apply"
else
  git -C "$WORKSPACE" apply --check "$PATCH_DIR/server.diff"
  git -C "$WORKSPACE" apply "$PATCH_DIR/server.diff"
fi

echo "[ok] Workspace prepared: $WORKSPACE"
echo "[next] Launch example (loopback-only):"
cat <<EOF
python -m mlx_lm.server \\
  --model <model> \\
  --host 127.0.0.1 \\
  --port 8130 \\
  --enable-optillm-decoding
EOF
