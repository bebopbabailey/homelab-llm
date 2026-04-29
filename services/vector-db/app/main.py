from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

from .backends import MemoryBackend, SearchArgs
from .config import CFG, memory_api_write_bearer_token, retrieval_profile
from .db import connect, ensure_schema, load_db_config
from .embed import EmbeddingRegistry

app = FastAPI(title="studio-memory-api", version="0.3.0")
_db_cfg = load_db_config()
_embed = EmbeddingRegistry()
_BACKEND: MemoryBackend | None = None


class EmbeddingsRequest(BaseModel):
    model: str
    input: list[str]


class ChunkRecord(BaseModel):
    chunk_id: str | None = None
    chunk_index: int = 0
    text: str
    section_title: str = ""
    timestamp_label: str = ""
    start_ms: int | None = None
    end_ms: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertDoc(BaseModel):
    document_id: str | None = None
    source_type: str = "generic"
    source: str
    source_thread_id: str = ""
    source_message_id: str = ""
    timestamp_utc: str | None = None
    title: str = ""
    uri: str = ""
    raw_ref: dict[str, Any] = Field(default_factory=dict)
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunks: list[ChunkRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_content(self) -> "UpsertDoc":
        if not self.text and not self.chunks:
            raise ValueError("upsert document requires text or chunks")
        return self


class UpsertRequest(BaseModel):
    documents: list[UpsertDoc]


class SearchRequest(BaseModel):
    query: str
    profile: Literal["precise", "balanced", "broad"] = "balanced"
    top_k: int | None = None
    lexical_k: int | None = None
    vector_k: int | None = None
    num_candidates: int | None = None
    final_k: int | None = None
    model_space: str = "nomic"
    document_id: str | None = None
    source_type: str | None = None
    source_types: list[str] = Field(default_factory=list)
    render_citations: bool | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    vector_search_mode: Literal["auto", "exact", "approximate"] = "auto"


class DeleteRequest(BaseModel):
    source: str | None = None
    document_id: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "DeleteRequest":
        if not self.source and not self.document_id:
            raise ValueError("delete requires source or document_id")
        return self


class ResponseMapUpsertRequest(BaseModel):
    response_id: str
    document_id: str
    source_type: str
    summary_mode: str


class ResponseMapResolveRequest(BaseModel):
    response_id: str


def _require_write_auth(authorization: str | None = Header(default=None)) -> None:
    expected = memory_api_write_bearer_token()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    actual = authorization.split(" ", 1)[1].strip()
    if actual != expected:
        raise HTTPException(status_code=403, detail="invalid bearer token")


def _get_backend() -> MemoryBackend:
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND

    if CFG.backend == "haystack":
        from .backends.haystack import HaystackBackend

        _BACKEND = cast(MemoryBackend, HaystackBackend())
    elif CFG.backend == "legacy":
        from .backends.legacy import LegacyBackend

        _BACKEND = cast(MemoryBackend, LegacyBackend())
    else:
        from .backends.elastic import ElasticBackend

        _BACKEND = cast(MemoryBackend, ElasticBackend())
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
def upsert(req: UpsertRequest, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    _require_write_auth(authorization)
    payload = []
    for d in req.documents:
        payload.append(
            {
                "document_id": d.document_id,
                "source_type": d.source_type,
                "source": d.source,
                "source_thread_id": d.source_thread_id,
                "source_message_id": d.source_message_id,
                "timestamp_utc": d.timestamp_utc,
                "title": d.title,
                "uri": d.uri,
                "raw_ref": d.raw_ref,
                "metadata": d.metadata,
                "text": d.text,
                "chunks": [chunk.model_dump() for chunk in d.chunks],
            }
        )
    counts = _get_backend().upsert(payload)
    return {"ok": True, **counts}


@app.post("/v1/memory/search")
def search(req: SearchRequest) -> dict[str, Any]:
    profile = retrieval_profile(req.profile)
    hits = _get_backend().search(
        SearchArgs(
            query=req.query,
            top_k=max(1, req.top_k or profile["final_k"]),
            lexical_k=max(1, req.lexical_k or profile["lexical_k"]),
            vector_k=max(1, req.vector_k or profile["vector_k"]),
            num_candidates=max(1, req.num_candidates or profile["num_candidates"]),
            final_k=max(1, req.final_k or req.top_k or profile["final_k"]),
            model_space=req.model_space,
            profile=profile["profile"],
            document_id=req.document_id,
            source_type=req.source_type,
            source_types=tuple(req.source_types),
            render_citations=profile["render_citations"] if req.render_citations is None else bool(req.render_citations),
            filters=req.filters,
            vector_search_mode=req.vector_search_mode,
        )
    )
    return {
        "query": req.query,
        "model_space": req.model_space,
        "profile": profile["profile"],
        "render_citations": profile["render_citations"] if req.render_citations is None else bool(req.render_citations),
        "hits": hits,
    }


@app.post("/v1/memory/delete")
def delete(req: DeleteRequest, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    _require_write_auth(authorization)
    n = _get_backend().delete(source=req.source, document_id=req.document_id)
    return {"ok": True, "deleted_documents": n}


@app.post("/v1/memory/response-map/upsert")
def upsert_response_map(
    req: ResponseMapUpsertRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    _require_write_auth(authorization)
    result = _get_backend().upsert_response_mapping(
        response_id=req.response_id,
        document_id=req.document_id,
        source_type=req.source_type,
        summary_mode=req.summary_mode,
    )
    return {"ok": True, **result}


@app.post("/v1/memory/response-map/resolve")
def resolve_response_map(req: ResponseMapResolveRequest) -> dict[str, Any]:
    result = _get_backend().resolve_response_mapping(req.response_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"response_id {req.response_id} not found")
    return {"ok": True, **result}
