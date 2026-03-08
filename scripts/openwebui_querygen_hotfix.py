#!/usr/bin/env python3
"""Idempotent runtime patch for Open WebUI web-search query generation.

Why this exists:
- Open WebUI 0.8.7 can treat query-generation responses as dict-only and
  fallback to `queries = [response]` on parse errors.
- In practice this can leak JSON/reasoning blobs into search `q`, degrading
  retrieval quality.

This script patches the installed middleware file in-place and is safe to run
repeatedly (no-op when already patched).
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import shutil
import sys

PATCH_MARKER = "querygen-hardening: avoid poisoned queries fallback"

OLD_BLOCK = """        response = res["choices"][0]["message"]["content"]

        try:
            bracket_start = response.find("{")
            bracket_end = response.rfind("}") + 1

            if bracket_start == -1 or bracket_end == -1:
                raise Exception("No JSON object found in the response")

            response = response[bracket_start:bracket_end]
            queries = json.loads(response)
            queries = queries.get("queries", [])
        except Exception as e:
            queries = [response]
"""

NEW_BLOCK = """        response_obj = res
        if hasattr(response_obj, "body"):
            try:
                body = getattr(response_obj, "body")
                if isinstance(body, bytes):
                    body = body.decode("utf-8", errors="replace")
                response_obj = json.loads(body)
            except Exception:
                response_obj = {}

        response = ""
        if isinstance(response_obj, dict):
            choices = response_obj.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0] if isinstance(choices[0], dict) else {}
                message = first_choice.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    response = content if isinstance(content, str) else str(content or "")

        try:
            bracket_start = response.find("{")
            bracket_end = response.rfind("}") + 1

            if bracket_start == -1 or bracket_end <= bracket_start:
                raise ValueError("no_json_object")

            response = response[bracket_start:bracket_end]
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                parsed_queries = parsed.get("queries", [])
                if isinstance(parsed_queries, list):
                    queries = [q.strip() for q in parsed_queries if isinstance(q, str) and q.strip()]
        except Exception as e:
            log.debug("querygen_parse_fallback user_message=%r error=%s", user_message, e)
            queries = [user_message]

        if not queries:
            queries = [user_message]
        # __PATCH_MARKER__
""".replace("__PATCH_MARKER__", PATCH_MARKER)


def patch_file(target: Path) -> tuple[bool, str]:
    content = target.read_text(encoding="utf-8")
    if PATCH_MARKER in content:
        return False, "already_patched"
    if OLD_BLOCK not in content:
        return False, "pattern_not_found"
    updated = content.replace(OLD_BLOCK, NEW_BLOCK)
    target.write_text(updated, encoding="utf-8")
    return True, "patched"


def make_backup(target: Path, backup_dir: Path | None) -> Path:
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d%H%M%S")
    if backup_dir is None:
        backup_dir = target.parent
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{target.name}.bak.querygen.{timestamp}"
    shutil.copy2(target, backup)
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch Open WebUI query generation fallback.")
    parser.add_argument("--target", required=True, help="Path to open_webui/utils/middleware.py")
    parser.add_argument("--backup-dir", default="", help="Optional backup directory")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"[openwebui_querygen_hotfix] target not found: {target}", file=sys.stderr)
        return 2

    backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else None
    backup = make_backup(target, backup_dir)
    changed, status = patch_file(target)
    print(
        f"[openwebui_querygen_hotfix] status={status} target={target} backup={backup}",
        file=sys.stdout,
    )
    return 0 if status in {"patched", "already_patched"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
