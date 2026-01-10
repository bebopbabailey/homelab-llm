#!/usr/bin/env python3
"""Demo MCP stdio client for the web.fetch tool."""

import argparse
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    parser = argparse.ArgumentParser(description="MCP web.fetch demo client")
    parser.add_argument(
        "--tool",
        choices=["web.fetch", "search.web"],
        default="web.fetch",
        help="Tool to call",
    )
    parser.add_argument("--url", default="https://example.com", help="URL to fetch")
    parser.add_argument("--query", default="openvino llm", help="Search query")
    parser.add_argument("--max-results", type=int, default=3, help="Search result count")
    parser.add_argument(
        "--print-clean-text",
        action="store_true",
        help="Print only clean_text",
    )
    args = parser.parse_args()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "web_fetch_mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if args.tool == "search.web":
                result = await session.call_tool(
                    "search.web",
                    {"query": args.query, "max_results": args.max_results},
                )
            else:
                result = await session.call_tool(
                    "web.fetch",
                    {"url": args.url, "include_raw_html": False},
                )
            if args.print_clean_text:
                payload = ""
                if result.content:
                    item = result.content[0]
                    payload = getattr(item, "text", "") or ""
                if payload:
                    try:
                        data = json.loads(payload)
                        print(data.get("clean_text", ""))
                    except json.JSONDecodeError:
                        print(payload)
            else:
                print(result)


if __name__ == "__main__":
    asyncio.run(main())
