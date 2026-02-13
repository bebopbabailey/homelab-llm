from __future__ import annotations

from pathlib import Path
import re


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def scaffold_tool(name: str, dest_root: str = "layer-tools/mcp-tools") -> Path:
    if not _NAME_RE.match(name):
        raise ValueError("Tool name must be kebab-case [a-z0-9-]")

    root = Path(dest_root)
    tool_dir = root / name
    if tool_dir.exists():
        raise FileExistsError(f"Tool already exists: {tool_dir}")

    tool_dir.mkdir(parents=True, exist_ok=False)
    (tool_dir / "README.md").write_text(
        f"# {name}\n\n"
        "Scaffolded MCP stdio tool skeleton.\n\n"
        "Status: NOT ENABLED until added to /etc/homelab-llm/mcp-registry.json\n",
        encoding="utf-8",
    )
    (tool_dir / "pyproject.toml").write_text(
        "[project]\n"
        f"name = \"{name}-mcp\"\n"
        "version = \"0.1.0\"\n"
        "requires-python = \">=3.10\"\n"
        "dependencies = [\"mcp>=1.0.0\"]\n\n"
        "[build-system]\n"
        "requires = [\"setuptools>=68\"]\n"
        "build-backend = \"setuptools.build_meta\"\n",
        encoding="utf-8",
    )
    (tool_dir / f"{name.replace('-', '_')}_mcp.py").write_text(
        "#!/usr/bin/env python3\n"
        "\"\"\"MCP tool skeleton.\"\"\"\n\n"
        "def main() -> None:\n"
        "    print('Implement MCP server here')\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )
    return tool_dir
