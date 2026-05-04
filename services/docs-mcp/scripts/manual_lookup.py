#!/usr/bin/env python3
"""Tiny helper for current docs-mcp phase-1 manual lookup workflows.

This helper is intentionally read-only for now. Use a full MCP client for
authoritative ingest operations.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_URL = "http://192.168.1.72:8013/mcp"
DEFAULT_LIBRARY = "library:music-manuals"
DEFAULT_DOCUMENT = "manual:music-manuals:reface-en-om-b0"
DEFAULT_RELATIVE_PATH = "reface_en_om_b0.pdf"
DEFAULT_TOKEN_FILE = "/Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Helper for docs-mcp manual ingest/search")
    parser.add_argument("--url", default=DEFAULT_URL, help="docs-mcp MCP endpoint")
    parser.add_argument("--token", default=None, help="docs-mcp bearer token")
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE, help="docs-mcp bearer token file")
    parser.add_argument("--read-timeout", type=float, default=120.0, help="per-tool MCP read timeout in seconds")
    parser.add_argument("--json", action="store_true", help="emit raw JSON results")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list registered libraries")

    ingest = sub.add_parser("ingest", help="UNDER CONSTRUCTION: ingest one manual")
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
    token = (args.token or os.getenv("DOCS_MCP_BEARER_TOKEN") or "").strip()
    if not token:
        token_file = (args.token_file or os.getenv("DOCS_MCP_BEARER_TOKEN_FILE") or "").strip()
        if token_file:
            try:
                token = Path(token_file).read_text(encoding="utf-8").strip()
            except OSError:
                token = ""
    read_timeout = dt.timedelta(seconds=max(1.0, float(args.read_timeout)))
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(headers=headers, follow_redirects=False, timeout=30.0, trust_env=False) as client:
        async with streamable_http_client(args.url, http_client=client, terminate_on_close=False) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if args.command == "list":
                    result = await session.call_tool("docs.library.list", {}, read_timeout_seconds=read_timeout)
                elif args.command == "ingest":
                    raise SystemExit(
                        "manual_lookup.py ingest is parked as UNDER CONSTRUCTION. "
                        "Use a real MCP client against docs.library.ingest for authoritative ingest."
                    )
                elif args.command == "search-document":
                    result = await session.call_tool(
                        "docs.document.search",
                        {
                            "document_handle": args.document_handle,
                            "query": args.query,
                        },
                        read_timeout_seconds=read_timeout,
                    )
                elif args.command == "search-library":
                    result = await session.call_tool(
                        "docs.library.search",
                        {
                            "library_handle": args.library_handle,
                            "query": args.query,
                        },
                        read_timeout_seconds=read_timeout,
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
