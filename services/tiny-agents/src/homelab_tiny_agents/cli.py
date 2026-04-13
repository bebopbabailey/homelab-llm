from __future__ import annotations

import argparse
import asyncio
import json

from .agent import TinyAgentRunner
from .models import ChatMessage, RunRequest
from .settings import load_settings
from .tool_scaffold import scaffold_tool


def main() -> None:
    parser = argparse.ArgumentParser(description="TinyAgents local orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-tools", help="List tools from MCP registry")

    run_p = sub.add_parser("run", help="Run one chat completion")
    run_p.add_argument("--model", required=True)
    run_p.add_argument("--message", required=True)
    run_p.add_argument("--max-tool-calls", type=int, default=1)
    run_p.add_argument("--allow-tool", action="append", default=None)

    scaffold_p = sub.add_parser("scaffold-tool", help="Scaffold a new MCP tool")
    scaffold_p.add_argument("name")

    args = parser.parse_args()
    settings = load_settings()

    if args.command == "scaffold-tool":
        out = scaffold_tool(args.name)
        print(json.dumps({"scaffolded": str(out)}))
        return

    runner = TinyAgentRunner(settings)

    if args.command == "list-tools":
        print(json.dumps({"tools": runner.list_tools()}, indent=2))
        return

    if args.command == "run":
        req = RunRequest(
            model=args.model,
            messages=[ChatMessage(role="user", content=args.message)],
            allowed_tools=args.allow_tool,
            max_tool_calls=args.max_tool_calls,
        )
        resp = asyncio.run(runner.run(req))
        print(resp.model_dump_json(indent=2))
        return


if __name__ == "__main__":
    main()
