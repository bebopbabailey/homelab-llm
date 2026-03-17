from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class MemoryServiceConfig:
    backend: str = os.getenv("MEMORY_BACKEND", "legacy")

    # Haystack pgvector configuration.
    hs_schema: str = os.getenv("MEMORY_HS_SCHEMA", "memory_hs")
    hs_table_qwen: str = os.getenv("MEMORY_HS_TABLE_QWEN", "memory_qwen")
    hs_table_mxbai: str = os.getenv("MEMORY_HS_TABLE_MXBAI", "memory_mxbai")
    hs_embedding_dimension: int = int(os.getenv("MEMORY_HS_EMBEDDING_DIM", "1024"))
    hs_vector_function: str = os.getenv("MEMORY_HS_VECTOR_FUNCTION", "cosine_similarity")
    hs_search_strategy: str = os.getenv("MEMORY_HS_SEARCH_STRATEGY", "hnsw")
    hs_allow_exact_fallback: bool = _env_bool("MEMORY_HS_ALLOW_EXACT_FALLBACK", True)
    hs_create_extension: bool = _env_bool("MEMORY_HS_CREATE_EXTENSION", True)

    # Query prompt discipline (documents remain unprompted).
    qwen_query_prefix: str = os.getenv(
        "MEMORY_QWEN_QUERY_PREFIX",
        "Instruct: Given a web search query, retrieve relevant passages that answer the query\\nQuery:",
    )
    mxbai_query_prefix: str = os.getenv(
        "MEMORY_MXBAI_QUERY_PREFIX",
        "Represent this sentence for searching relevant passages: ",
    )

    # Reranker controls.
    rerank_enabled: bool = _env_bool("MEMORY_RERANK_ENABLED", True)
    rerank_fail_open: bool = _env_bool("MEMORY_RERANK_FAIL_OPEN", True)
    rerank_model: str = os.getenv(
        "MEMORY_RERANK_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
    )

    # Ingest mode controls.
    ingest_mode: str = os.getenv("MEMORY_INGEST_MODE", "jsonl")
    manuals_pdf_glob: str = os.getenv("MEMORY_MANUALS_PDF_GLOB", "")
    manuals_source: str = os.getenv("MEMORY_MANUALS_SOURCE", "manuals_pdf")


CFG = MemoryServiceConfig()
