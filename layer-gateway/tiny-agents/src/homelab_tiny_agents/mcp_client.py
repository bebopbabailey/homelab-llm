from __future__ import annotations

import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .models import McpServerSpec


class MCPToolClient:
    async def call_tool(
        self,
        *,
        server: McpServerSpec,
        tool_name: str,
        input_json: dict[str, Any],
    ) -> dict[str, Any]:
        if server.transport != "stdio":
            raise RuntimeError(f"Unsupported transport for MVP: {server.transport}")
        if not server.command:
            raise RuntimeError(f"Missing command for MCP server: {server.name}")

        env = os.environ.copy()
        for env_name in server.env:
            env.setdefault(env_name, os.getenv(env_name, ""))

        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=env,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, input_json)

        # mcp SDK result shape can vary; normalize to dict for downstream logging
        if hasattr(result, "model_dump"):
            return result.model_dump()  # type: ignore[no-any-return]
        if isinstance(result, dict):
            return result
        return {"result": str(result)}
