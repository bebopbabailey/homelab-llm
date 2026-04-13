#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description="Start a raw Studio llama-server mirror via ssh.")
    parser.add_argument("--host", default="studio")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--alias", required=True)
    parser.add_argument(
        "--server-bin",
        default="/Users/thestudio/llama.cpp/build/bin/llama-server",
        help="Versioned raw llama-server path on Studio.",
    )
    parser.add_argument("--ctx-size", default="0")
    parser.add_argument("--ubatch-size", default="2048")
    parser.add_argument("--batch-size", default="2048")
    parser.add_argument("--bind-host", default="127.0.0.1")
    args = parser.parse_args()

    log = f"/Users/thestudio/Library/Logs/llama-mirror-{args.port}.log"
    err = f"/Users/thestudio/Library/Logs/llama-mirror-{args.port}.err"
    pid = f"/tmp/llama-mirror-{args.port}.pid"
    cmd = [
        args.server_bin,
        "--model",
        args.model_path,
        "--alias",
        args.alias,
        "--host",
        args.bind_host,
        "--port",
        str(args.port),
        "--ctx-size",
        str(args.ctx_size),
        # GPT-OSS uses the built-in Jinja template path on llama.cpp.
        "--jinja",
        "-ub",
        str(args.ubatch_size),
        "-b",
        str(args.batch_size),
    ]
    remote = (
        f"nohup {' '.join(shlex.quote(part) for part in cmd)} "
        f">{shlex.quote(log)} 2>{shlex.quote(err)} < /dev/null & echo $! > {shlex.quote(pid)}"
    )
    subprocess.run(["ssh", args.host, remote], check=True)
    print(f"started mirror on {args.host}:{args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
