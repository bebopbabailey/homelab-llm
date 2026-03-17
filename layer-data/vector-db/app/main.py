from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .backends import MemoryBackend, SearchArgs
from .config import CFG
from .db import connect, ensure_schema, load_db_config
from .embed import EmbeddingRegistry

app = FastAPI(title="studio-memory-api", version="0.2.0")
_db_cfg = load_db_config()
_embed = EmbeddingRegistry()
_BACKEND: MemoryBackend | None = None


class EmbeddingsRequest(BaseModel):
    model: str
    input: list[str]


class UpsertDoc(BaseModel):
    source: str
    source_thread_id: str = ""
    source_message_id: str = ""
    timestamp_utc: str | None = None
    title: str = ""
    uri: str = ""
    raw_ref: dict[str, Any] = Field(default_factory=dict)
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertRequest(BaseModel):
    documents: list[UpsertDoc]


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    lexical_k: int = 30
    vector_k: int = 30
    model_space: Literal["qwen", "mxbai"] = "qwen"


class DeleteRequest(BaseModel):
    source: str


def _get_backend() -> MemoryBackend:
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND

    if CFG.backend == "haystack":
        from .backends.haystack import HaystackBackend

        _BACKEND = cast(MemoryBackend, HaystackBackend())
    else:
        from .backends.legacy import LegacyBackend

        _BACKEND = cast(MemoryBackend, LegacyBackend())
    return _BACKEND


@app.on_event("startup")
def _startup() -> None:
    auto_init = os.getenv("MEMORY_DB_AUTO_INIT", "false").lower() == "true"
    if auto_init and CFG.backend == "legacy":
        sql_dir = Path(__file__).resolve().parents[1] / "sql"
        with connect(_db_cfg) as conn:
            ensure_schema(conn, sql_dir)
    _get_backend()


@app.get("/health")
def get_health() -> dict[str, Any]:
    try:
        info = _get_backend().health()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"backend_unhealthy: {exc}") from exc
    return {"service": "studio-memory-api", **info}


@app.get("/v1/memory/stats")
def get_stats() -> dict[str, Any]:
    return _get_backend().stats()


@app.post("/v1/embeddings")
def embeddings(req: EmbeddingsRequest) -> dict[str, Any]:
    vectors = _embed.embed(req.model, req.input)
    return {
        "object": "list",
        "model": req.model,
        "data": [
            {"object": "embedding", "index": i, "embedding": vec}
            for i, vec in enumerate(vectors)
        ],
    }


@app.post("/v1/memory/upsert")
def upsert(req: UpsertRequest) -> dict[str, Any]:
    payload = [
        {
            "source": d.source,
            "source_thread_id": d.source_thread_id,
            "source_message_id": d.source_message_id,
            "timestamp_utc": d.timestamp_utc,
            "title": d.title,
            "uri": d.uri,
            "raw_ref": d.raw_ref,
            "content_hash": "",
            "metadata": d.metadata,
            "text": d.text,
            "chunk_index": 0,
        }
        for d in req.documents
    ]
    counts = _get_backend().upsert(payload)
    return {"ok": True, **counts}


@app.post("/v1/memory/search")
def search(req: SearchRequest) -> dict[str, Any]:
    hits = _get_backend().search(
        SearchArgs(
            query=req.query,
            top_k=max(1, req.top_k),
            lexical_k=max(1, req.lexical_k),
            vector_k=max(1, req.vector_k),
            model_space=req.model_space,
        )
    )
    return {"query": req.query, "model_space": req.model_space, "hits": hits}


@app.post("/v1/memory/delete")
def delete(req: DeleteRequest) -> dict[str, Any]:
    n = _get_backend().delete(req.source)
    return {"ok": True, "deleted_documents": n}
