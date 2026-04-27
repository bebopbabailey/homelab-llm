from __future__ import annotations

import argparse
import json
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
SOURCE_CONFIG = SERVICE_ROOT / "langgraph.json"
DEFAULT_OUTPUT = Path.home() / ".local" / "state" / "orchestration-cockpit" / "langgraph-runtime" / "langgraph.json"


def _resolve_dependency(entry: str) -> str:
    return str((SERVICE_ROOT / entry).resolve())


def _resolve_graph(entry: str) -> str:
    path_text, variable = entry.rsplit(":", 1)
    return f"{(SERVICE_ROOT / path_text).resolve()}:{variable}"


def render_runtime_config() -> str:
    data = json.loads(SOURCE_CONFIG.read_text(encoding="utf-8"))
    rendered = {
        "dependencies": [_resolve_dependency(entry) for entry in data.get("dependencies", [])],
        "graphs": {
            graph_id: _resolve_graph(spec)
            for graph_id, spec in data.get("graphs", {}).items()
        },
    }
    return json.dumps(rendered, indent=2, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the generated runtime langgraph.json with absolute paths."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render_runtime_config()
    if args.check:
        current = args.output.read_text(encoding="utf-8")
        if current != rendered:
            raise SystemExit(f"{args.output} is stale; re-run render_langgraph_runtime_config.py")
        print(f"Runtime config up to date: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote runtime config: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
