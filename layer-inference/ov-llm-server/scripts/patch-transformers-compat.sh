#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${1:-$SCRIPT_DIR/../.venv-convert}"
PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing venv python at $PYTHON" >&2
  exit 1
fi

"$PYTHON" - <<'PY'
from __future__ import annotations

from pathlib import Path

import transformers
from transformers.cache_utils import DynamicCache
from transformers import utils as tf_utils

site = Path(transformers.__file__).resolve().parent
cache_utils = site / "cache_utils.py"
utils_init = site / "utils" / "__init__.py"

patched = []

if not hasattr(DynamicCache, "get_usable_length"):
    text = cache_utils.read_text()
    marker = "class StaticCache"
    insert = (
        "\n    def get_usable_length(self, new_seq_length: int | None = None, layer_idx: int = 0) -> int:\n"
        "        \"\"\"Compatibility shim for models expecting get_usable_length on DynamicCache.\"\"\"\n"
        "        return self.get_seq_length(layer_idx)\n"
    )
    if "get_usable_length" not in text:
        parts = text.split(marker)
        if len(parts) < 2:
            raise RuntimeError("Failed to patch cache_utils.py (StaticCache marker missing).")
        before = parts[0].rstrip() + insert + "\n\n" + marker
        text = before + marker.join(parts[1:])
        cache_utils.write_text(text)
        patched.append("DynamicCache.get_usable_length")

if not hasattr(tf_utils, "LossKwargs"):
    text = utils_init.read_text()
    if "class LossKwargs" not in text:
        text = text.rstrip() + "\n\n\n# Compatibility shim for models that import LossKwargs from transformers.utils.\nclass LossKwargs(TransformersKwargs):\n    pass\n"
        utils_init.write_text(text)
        patched.append("utils.LossKwargs")

if patched:
    print("Patched:", ", ".join(patched))
else:
    print("No patches needed.")
PY
