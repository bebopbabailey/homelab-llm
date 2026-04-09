#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def iter_docs() -> list[Path]:
    docs: list[Path] = []
    for path in ROOT.rglob("*.md"):
        rel = path.relative_to(ROOT)
        if any(part.startswith(".venv") for part in rel.parts):
            continue
        if "site-packages" in rel.parts:
            continue
        if rel.parts[:2] == ("layer-tools", "searxng") and "app" in rel.parts:
            continue
        if len(rel.parts) == 1:
            docs.append(path)
        elif rel.parts[0] == "docs":
            docs.append(path)
        elif rel.parts[0].startswith("layer-"):
            docs.append(path)
        elif rel == Path("platform/ops/README.md") or rel == Path("scripts/README.md"):
            docs.append(path)
    return sorted(docs)


def resolve_link(source: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    if target.startswith("/"):
        return ROOT / target.lstrip("/")
    return (source.parent / target).resolve()


def main() -> int:
    missing: list[tuple[str, str]] = []
    for doc in iter_docs():
        text = doc.read_text(encoding="utf-8", errors="ignore")
        for target in LINK_RE.findall(text):
            resolved = resolve_link(doc, target)
            if resolved is not None and not resolved.exists():
                missing.append((str(doc.relative_to(ROOT)), target))

    if missing:
        for doc, target in missing:
            print(f"{doc}: {target}")
        print(f"TOTAL_MISSING {len(missing)}")
        return 1

    print("ok: internal markdown links resolve on the supported documentation surface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
