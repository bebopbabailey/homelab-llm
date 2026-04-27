from __future__ import annotations

import json
import os
from pathlib import Path

from orchestration_cockpit.graph import build_graph
from orchestration_cockpit.observability import artifact_dir, graph_id, run_ledger_path
from render_graph_diagram import DEFAULT_OUTPUT, render_mermaid


def main() -> int:
    graph = build_graph()
    if graph is None:
        raise SystemExit("graph did not compile")

    if not DEFAULT_OUTPUT.exists():
        raise SystemExit(f"missing Mermaid artifact: {DEFAULT_OUTPUT}")
    expected = render_mermaid()
    current = DEFAULT_OUTPUT.read_text(encoding="utf-8")
    if current != expected:
        raise SystemExit(f"stale Mermaid artifact: {DEFAULT_OUTPUT}")

    summary = {
        "graph_id": graph_id(),
        "artifact_dir": str(artifact_dir()),
        "run_ledger_path": str(run_ledger_path()),
        "langsmith_key_present": bool(os.environ.get("LANGSMITH_API_KEY")),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
