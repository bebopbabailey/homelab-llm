from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def emit_log(*, event: str, log_path: Path | None, **fields: Any) -> None:
    payload = {"ts_utc": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    line = json.dumps(payload, sort_keys=True)
    print(line, file=sys.stdout)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
