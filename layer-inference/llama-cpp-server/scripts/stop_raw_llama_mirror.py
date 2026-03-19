#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop a raw Studio llama-server mirror via ssh.")
    parser.add_argument("--host", default="studio")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    pid = f"/tmp/llama-mirror-{args.port}.pid"
    remote = f"if [ -f {pid} ]; then kill $(cat {pid}) 2>/dev/null || true; rm -f {pid}; fi"
    subprocess.run(["ssh", args.host, remote], check=True)
    print(f"stopped mirror on {args.host}:{args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
