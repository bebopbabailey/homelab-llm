from __future__ import annotations

import argparse
from pathlib import Path

from orchestration_cockpit.graph import build_graph

SERVICE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = SERVICE_ROOT / "docs" / "operator-cockpit.mmd"
HEADER = "<!-- generated from services/orchestration-cockpit/src/orchestration_cockpit/graph.py; do not edit by hand -->\n"


def render_mermaid() -> str:
    graph = build_graph().get_graph()
    return f"{HEADER}{graph.draw_mermaid().rstrip()}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the orchestration-cockpit Mermaid graph.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render_mermaid()
    if args.check:
        current = args.output.read_text(encoding="utf-8")
        if current != rendered:
            raise SystemExit(f"{args.output} is stale; re-run render_graph_diagram.py")
        print(f"Mermaid graph up to date: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote Mermaid graph: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
