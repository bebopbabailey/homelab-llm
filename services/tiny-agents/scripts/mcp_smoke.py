#!/usr/bin/env python3
"""Smoke test for MCP tools (search.web + web.fetch)."""

import argparse
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    parser = argparse.ArgumentParser(description="MCP tool smoke test")
    parser.add_argument(
        "--tool",
        choices=["search.web", "web.fetch"],
        default="search.web",
        help="Tool to call",
    )
    parser.add_argument("--query", default="openvino llm", help="Search query")
    parser.add_argument("--max-results", type=int, default=3, help="Search result count")
    parser.add_argument("--url", default="https://example.com", help="URL to fetch")
    args = parser.parse_args()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "web_fetch_mcp"],
        env=os.environ.copy(),
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
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
