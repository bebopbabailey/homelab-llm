#!/usr/bin/env python3
from __future__ import annotations

import json

from app.backends.haystack import HaystackBackend
from app.config import CFG
from app.db import connect, load_db_config


def main() -> None:
    cfg = load_db_config()
    with connect(cfg) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {CFG.hs_schema}")
        conn.commit()

    backend = HaystackBackend(warm_models=False)
    stats = backend.stats()
    print(json.dumps({"ok": True, "backend": "haystack", "stats": stats}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
