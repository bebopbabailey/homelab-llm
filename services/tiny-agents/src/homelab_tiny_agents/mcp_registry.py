from __future__ import annotations

import json
from pathlib import Path

from .models import McpServerSpec


def load_registry(path: str) -> list[McpServerSpec]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"MCP registry not found: {path}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    servers = raw.get("servers", [])
    return [McpServerSpec.model_validate(s) for s in servers]


def build_tool_index(servers: list[McpServerSpec]) -> dict[str, McpServerSpec]:
    index: dict[str, McpServerSpec] = {}
    for server in servers:
        for tool in server.tools:
            index[tool] = server
    return index
