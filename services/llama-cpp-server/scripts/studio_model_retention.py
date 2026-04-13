#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


DEFAULT_HOST = "studio"
HF_MODELS_ROOT = "/Users/thestudio/models/hf"
HF_CACHE_ROOT = "/Users/thestudio/.cache/huggingface/hub"
LLAMA_CACHE_ROOT = "/Users/thestudio/Library/Caches/llama.cpp"
LMSTUDIO_MODELS_ROOT = "/Users/thestudio/.lmstudio/models"

DEFAULT_KEEP_SLUGS_BY_ROOT = {
    HF_MODELS_ROOT: {
        "qwen3-next-80b-a3b-instruct-mlx-mxfp4",
    },
    LMSTUDIO_MODELS_ROOT: {
        "gpt-oss-20b-gguf",
        "gpt-oss-120b-gguf",
    },
}
EXPLICIT_DELETE_TARGETS = {
    "gemma-3-27b-it-qat-4bit",
    "glm-4.7-flash-4bit-mxfp4",
    "gpt-oss-120b-mxfp4-q4",
    "gpt-oss-20b-mxfp4-q4",
    "llama-3.3-70b-instruct-4bit",
    "seed-oss-36b-instruct-4bit",
    "gpt-oss-120b-derestricted-mxfp4-mlx",
}


def _run_ssh(host: str, remote_cmd: str) -> str:
    proc = subprocess.run(
        ["ssh", host, remote_cmd],
        check=True,
        text=True,
        capture_output=True,
    )
    return proc.stdout


def _normalize_slug(text: str) -> str:
    lowered = text.lower().replace("_", "-")
    lowered = lowered.replace("models--", "")
    lowered = lowered.replace("ggml-org-", "")
    lowered = lowered.replace("mlx-community-", "")
    lowered = lowered.replace("libraxisai-", "")
    lowered = lowered.replace("txgsync-", "")
    lowered = lowered.replace("--", "-")
    lowered = lowered.replace("/", "-")
    return lowered


def _path_slug(path: str) -> str:
    name = PurePosixPath(path).name
    if name.endswith(".etag"):
        name = name[:-5]
    if name.endswith(".gguf"):
        name = name[:-5]
    return _normalize_slug(name)


@dataclass
class Entry:
    path: str
    size_bytes: int
    slug: str
    action: str
    reason: str


def _keep_slugs_for_path(path: str, extra_keep_slugs: set[str]) -> set[str]:
    keep_slugs = set(extra_keep_slugs)
    for root, root_keep_slugs in DEFAULT_KEEP_SLUGS_BY_ROOT.items():
        if path == root or path.startswith(f"{root}/"):
            keep_slugs.update(root_keep_slugs)
    return keep_slugs


def _classify(path: str, size_bytes: int, keep_slugs: set[str], staged_slug: str | None) -> Entry:
    slug = _path_slug(path)
    effective_keep_slugs = _keep_slugs_for_path(path, keep_slugs)
    keep_match = next((item for item in effective_keep_slugs if item in slug), None)
    staged_match = staged_slug if staged_slug and staged_slug in slug else None
    explicit_delete = next((item for item in EXPLICIT_DELETE_TARGETS if item in slug), None)

    if keep_match:
        return Entry(path, size_bytes, slug, "keep", f"active_keep:{keep_match}")
    if staged_match:
        return Entry(path, size_bytes, slug, "stage", f"staged_next:{staged_match}")
    if explicit_delete:
        return Entry(path, size_bytes, slug, "delete", f"explicit_delete_target:{explicit_delete}")
    return Entry(path, size_bytes, slug, "delete", "not_in_keep_set")


def _inventory(host: str, roots: Iterable[str]) -> list[tuple[str, int]]:
    remote_cmd = (
        "python3 - <<'PY'\n"
        "import json, os\n"
        f"roots = {json.dumps(list(roots))}\n"
        "out = []\n"
        "for root in roots:\n"
        "    if not os.path.exists(root):\n"
        "        continue\n"
        "    if not os.path.isdir(root):\n"
        "        continue\n"
        "    entries = []\n"
        "    if root.endswith('.lmstudio/models'):\n"
        "        for publisher in os.listdir(root):\n"
        "            publisher_path = os.path.join(root, publisher)\n"
        "            if not os.path.isdir(publisher_path):\n"
        "                continue\n"
        "            for model_name in os.listdir(publisher_path):\n"
        "                entries.append(os.path.join(publisher_path, model_name))\n"
        "    else:\n"
        "        entries = [os.path.join(root, entry) for entry in os.listdir(root)]\n"
        "    for path in entries:\n"
        "        entry = os.path.basename(path)\n"
        "        if root.endswith('Library/Caches/llama.cpp') and not entry.endswith('.gguf'):\n"
        "            continue\n"
        "        try:\n"
        "            if os.path.isdir(path):\n"
        "                total = 0\n"
        "                for dirpath, _, filenames in os.walk(path):\n"
        "                    for filename in filenames:\n"
        "                        fp = os.path.join(dirpath, filename)\n"
        "                        try:\n"
        "                            total += os.path.getsize(fp)\n"
        "                        except OSError:\n"
        "                            pass\n"
        "                out.append({'path': path, 'size_bytes': total})\n"
        "            elif os.path.isfile(path):\n"
        "                out.append({'path': path, 'size_bytes': os.path.getsize(path)})\n"
        "        except OSError:\n"
        "            pass\n"
        "print(json.dumps(out))\n"
        "PY"
    )
    payload = json.loads(_run_ssh(host, remote_cmd) or "[]")
    return [(item["path"], int(item["size_bytes"])) for item in payload]


def _delete(host: str, paths: Iterable[str]) -> None:
    path_list = list(paths)
    if not path_list:
        return
    quoted = " ".join(shlex.quote(path) for path in path_list)
    _run_ssh(host, f"rm -rf {quoted}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory and prune Studio model artifacts.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--staged-slug", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", default="-")
    parser.add_argument("--keep-slug", action="append", default=[])
    args = parser.parse_args()

    roots = [
        HF_MODELS_ROOT,
        HF_CACHE_ROOT,
        LLAMA_CACHE_ROOT,
        LMSTUDIO_MODELS_ROOT,
    ]
    keep_slugs = {_normalize_slug(item) for item in args.keep_slug}
    staged_slug = _normalize_slug(args.staged_slug) if args.staged_slug else None

    entries = [
        _classify(path, size_bytes, keep_slugs, staged_slug)
        for path, size_bytes in _inventory(args.host, roots)
    ]
    entries.sort(key=lambda item: (item.action, -item.size_bytes, item.path))

    manifest = {
        "host": args.host,
        "roots": roots,
        "default_keep_slugs_by_root": {
            root: sorted(slugs) for root, slugs in sorted(DEFAULT_KEEP_SLUGS_BY_ROOT.items())
        },
        "keep_slugs": sorted(keep_slugs),
        "staged_slug": staged_slug,
        "entries": [
            {
                "path": entry.path,
                "size_bytes": entry.size_bytes,
                "slug": entry.slug,
                "action": entry.action,
                "reason": entry.reason,
            }
            for entry in entries
        ],
    }

    if args.apply:
        delete_paths = [entry.path for entry in entries if entry.action == "delete"]
        _delete(args.host, delete_paths)
        manifest["applied_delete_count"] = len(delete_paths)

    output = json.dumps(manifest, indent=2, sort_keys=True)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w", encoding="ascii") as handle:
            handle.write(output)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
