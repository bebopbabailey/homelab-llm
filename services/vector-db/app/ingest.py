from __future__ import annotations

import hashlib
import glob
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .backends.base import MemoryBackend
from .config import CFG
from .db import connect, load_db_config, record_ingest_run


@dataclass(frozen=True)
class ChunkPolicy:
    max_chars: int = 2200
    overlap_chars: int = 180


def _chunk_text(text: str, policy: ChunkPolicy) -> list[str]:
    text = (text or "").strip()
    if not text:
        return [""]
    if len(text) <= policy.max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + policy.max_chars)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - policy.overlap_chars)
    return chunks or [text]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_backend() -> MemoryBackend:
    if CFG.backend == "haystack":
        from .backends.haystack import HaystackBackend

        return HaystackBackend()
    from .backends.legacy import LegacyBackend

    return LegacyBackend()


def _jsonl_records(jsonl_path: Path, policy: ChunkPolicy) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text = str(rec.get("text", "") or "")
            pieces = _chunk_text(text, policy)
            for idx, chunk in enumerate(pieces):
                out.append(
                    {
                        "source": str(rec.get("source", "unknown")),
                        "source_thread_id": str(rec.get("source_thread_id", "")),
                        "source_message_id": str(rec.get("source_message_id", rec.get("id", ""))),
                        "timestamp_utc": rec.get("timestamp"),
                        "title": str(rec.get("title", "")),
                        "uri": str(rec.get("uri", "")),
                        "raw_ref": rec.get("raw_ref", {}),
                        "content_hash": _content_hash(chunk),
                        "metadata": {"schema_version": rec.get("schema_version", "events.v0")},
                        "text": chunk,
                        "chunk_index": idx,
                    }
                )
    return out


def _manuals_pdf_records(pdf_glob: str, source: str, policy: ChunkPolicy) -> list[dict[str, Any]]:
    try:
        from haystack import Pipeline
        from haystack.components.converters import PyPDFToDocument
        from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "manuals_pdf ingest requires haystack converter/preprocessor dependencies"
        ) from exc

    files = sorted(glob.glob(pdf_glob, recursive=True))
    if not files:
        raise RuntimeError(f"no PDF files found for MEMORY_MANUALS_PDF_GLOB={pdf_glob!r}")

    pipe = Pipeline()
    pipe.add_component("convert", PyPDFToDocument())
    pipe.add_component("clean", DocumentCleaner())
    pipe.add_component(
        "split",
        DocumentSplitter(split_by="word", split_length=max(1, policy.max_chars // 5), split_overlap=max(0, policy.overlap_chars // 5)),
    )
    pipe.connect("convert.documents", "clean.documents")
    pipe.connect("clean.documents", "split.documents")

    result = pipe.run({"convert": {"sources": files}})
    docs = result.get("split", {}).get("documents", [])

    out: list[dict[str, Any]] = []
    for idx, d in enumerate(docs):
        meta = d.meta or {}
        text = str(d.content or "")
        out.append(
            {
                "source": source,
                "source_thread_id": str(meta.get("file_path", "")),
                "source_message_id": str(idx),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "title": str(meta.get("file_name", "")),
                "uri": str(meta.get("file_path", "")),
                "raw_ref": {"converter": "PyPDFToDocument"},
                "content_hash": _content_hash(text),
                "metadata": {"schema_version": "manuals_pdf.v1", "page_number": meta.get("page_number")},
                "text": text,
                "chunk_index": int(meta.get("split_id", idx)),
            }
        )
    return out


def run_ingest() -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("INGEST-%Y%m%d-%H%M%S")
    policy = ChunkPolicy(
        max_chars=int(os.getenv("MEMORY_CHUNK_MAX_CHARS", "2200")),
        overlap_chars=int(os.getenv("MEMORY_CHUNK_OVERLAP_CHARS", "180")),
    )

    backend = _load_backend()
    if CFG.ingest_mode == "manuals_pdf":
        if not CFG.manuals_pdf_glob:
            raise RuntimeError("MEMORY_MANUALS_PDF_GLOB is required when MEMORY_INGEST_MODE=manuals_pdf")
        records = _manuals_pdf_records(CFG.manuals_pdf_glob, CFG.manuals_source, policy)
        ingest_input = CFG.manuals_pdf_glob
    else:
        path = Path(os.getenv("MEMORY_INGEST_PATH", ""))
        if not path:
            raise RuntimeError("MEMORY_INGEST_PATH is required when MEMORY_INGEST_MODE=jsonl")
        records = _jsonl_records(path, policy)
        ingest_input = str(path)

    counts = backend.upsert(records)
    docs = int(counts.get("documents", 0))
    chunks = int(counts.get("chunks", 0))

    # Preserve ingest run audit trail for both backends.
    cfg = load_db_config()
    with connect(cfg) as conn:
        run = {
            "run_id": run_id,
            "status": "ok",
            "docs": docs,
            "chunks": chunks,
            "input": ingest_input,
            "backend": CFG.backend,
            "ingest_mode": CFG.ingest_mode,
        }
        record_ingest_run(conn, run)
        conn.commit()

    return run


if __name__ == "__main__":
    report = run_ingest()
    print(json.dumps(report, indent=2, sort_keys=True))
