#!/usr/bin/env python3
"""Tiny helper for current docs-mcp phase-1 manual workflows."""

from __future__ import annotations

import argparse
import json
from typing import Any

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = "http://127.0.0.1:8013/mcp"
DEFAULT_LIBRARY = "library:music-manuals"
DEFAULT_DOCUMENT = "manual:music-manuals:reface-en-om-b0"
DEFAULT_RELATIVE_PATH = "reface_en_om_b0.pdf"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Helper for docs-mcp manual ingest/search")
    parser.add_argument("--url", default=DEFAULT_URL, help="docs-mcp MCP endpoint")
    parser.add_argument("--json", action="store_true", help="emit raw JSON results")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list registered libraries")

    ingest = sub.add_parser("ingest", help="ingest one manual")
    ingest.add_argument("--library-handle", default=DEFAULT_LIBRARY)
    ingest.add_argument("--relative-path", default=DEFAULT_RELATIVE_PATH)
    ingest.add_argument("--dry-run", action="store_true")

    search_doc = sub.add_parser("search-document", help="search one document handle")
    search_doc.add_argument("--document-handle", default=DEFAULT_DOCUMENT)
    search_doc.add_argument("--query", required=True)

    search_lib = sub.add_parser("search-library", help="search one library handle")
    search_lib.add_argument("--library-handle", default=DEFAULT_LIBRARY)
    search_lib.add_argument("--query", required=True)

    return parser


def _content_to_python(content: list[Any]) -> Any:
    items: list[Any] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is None:
            items.append({"type": getattr(item, "type", "unknown")})
            continue
        try:
            items.append(json.loads(text))
        except json.JSONDecodeError:
            items.append(text)
    if len(items) == 1:
        return items[0]
    return items


def _print_human(result: Any) -> None:
    if isinstance(result, dict):
        print(json.dumps(result, indent=2))
        return
    if isinstance(result, list):
        for item in result:
            if isinstance(item, (dict, list)):
                print(json.dumps(item, indent=2))
            else:
                print(item)
        return
    print(result)


async def _run(args: argparse.Namespace) -> None:
    async with streamablehttp_client(args.url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if args.command == "list":
                result = await session.call_tool("docs.library.list", {})
            elif args.command == "ingest":
                result = await session.call_tool(
                    "docs.library.ingest",
                    {
                        "library_handle": args.library_handle,
                        "relative_path": args.relative_path,
                        "dry_run": bool(args.dry_run),
                    },
                )
            elif args.command == "search-document":
                result = await session.call_tool(
                    "docs.document.search",
                    {
                        "document_handle": args.document_handle,
                        "query": args.query,
                    },
                )
            elif args.command == "search-library":
                result = await session.call_tool(
                    "docs.library.search",
                    {
                        "library_handle": args.library_handle,
                        "query": args.query,
                    },
                )
            else:
                raise SystemExit(f"unsupported command: {args.command}")

    payload = _content_to_python(result.content)
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    _print_human(payload)


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    anyio.run(_run, args)


if __name__ == "__main__":
    main()
