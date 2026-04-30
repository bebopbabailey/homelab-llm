from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_secret(name: str, file_name: str) -> str:
    raw = os.getenv(name)
    if raw:
        return raw
    path = os.getenv(file_name)
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


@dataclass(frozen=True)
class MemoryServiceConfig:
    backend: str = os.getenv("MEMORY_BACKEND", "elastic")

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
    write_bearer_token: str = _env_secret("MEMORY_API_WRITE_BEARER_TOKEN", "MEMORY_API_WRITE_BEARER_TOKEN_FILE")

    # Elastic runtime and retrieval configuration.
    elastic_url: str = os.getenv("MEMORY_ELASTIC_URL", "http://127.0.0.1:9200")
    elastic_api_key: str | None = os.getenv("MEMORY_ELASTIC_API_KEY")
    elastic_username: str | None = os.getenv("MEMORY_ELASTIC_USERNAME")
    elastic_password: str | None = os.getenv("MEMORY_ELASTIC_PASSWORD")
    elastic_verify_certs: bool = _env_bool("MEMORY_ELASTIC_VERIFY_CERTS", True)
    elastic_request_timeout_seconds: int = _env_int("MEMORY_ELASTIC_TIMEOUT_SECONDS", 20)
    elastic_min_supported_version: str = os.getenv("MEMORY_ELASTIC_MIN_VERSION", "8.19.0")
    elastic_preferred_version: str = os.getenv("MEMORY_ELASTIC_PREFERRED_VERSION", "9.2.0")
    elastic_chunks_alias: str = os.getenv("MEMORY_ELASTIC_CHUNKS_ALIAS", "memory-chunks-current")
    elastic_documents_index: str = os.getenv("MEMORY_ELASTIC_DOCUMENTS_INDEX", "memory-documents-v1")
    elastic_response_map_index: str = os.getenv("MEMORY_ELASTIC_RESPONSE_MAP_INDEX", "memory-response-map-v1")
    elastic_similarity: str = os.getenv("MEMORY_ELASTIC_SIMILARITY", "cosine")
    elastic_index_type: str = os.getenv("MEMORY_ELASTIC_INDEX_TYPE", "int8_hnsw")
    elastic_hnsw_m: int = _env_int("MEMORY_ELASTIC_HNSW_M", 16)
    elastic_hnsw_ef_construction: int = _env_int("MEMORY_ELASTIC_HNSW_EF_CONSTRUCTION", 100)
    elastic_enable_native_rrf: bool = _env_bool("MEMORY_ELASTIC_ENABLE_NATIVE_RRF", True)
    elastic_single_doc_exact_max_chunks: int = _env_int("MEMORY_SINGLE_DOC_EXACT_MAX_CHUNKS", 1024)
    elastic_rrf_rank_constant: int = _env_int("MEMORY_RRF_RANK_CONSTANT", 60)
    elastic_profile_precise_lexical_k: int = _env_int("MEMORY_PROFILE_PRECISE_LEXICAL_K", 24)
    elastic_profile_precise_vector_k: int = _env_int("MEMORY_PROFILE_PRECISE_VECTOR_K", 24)
    elastic_profile_precise_num_candidates: int = _env_int("MEMORY_PROFILE_PRECISE_NUM_CANDIDATES", 96)
    elastic_profile_precise_final_k: int = _env_int("MEMORY_PROFILE_PRECISE_FINAL_K", 8)
    elastic_profile_precise_render_citations: bool = _env_bool("MEMORY_PROFILE_PRECISE_RENDER_CITATIONS", True)
    elastic_profile_balanced_lexical_k: int = _env_int("MEMORY_PROFILE_BALANCED_LEXICAL_K", 48)
    elastic_profile_balanced_vector_k: int = _env_int("MEMORY_PROFILE_BALANCED_VECTOR_K", 48)
    elastic_profile_balanced_num_candidates: int = _env_int("MEMORY_PROFILE_BALANCED_NUM_CANDIDATES", 192)
    elastic_profile_balanced_final_k: int = _env_int("MEMORY_PROFILE_BALANCED_FINAL_K", 10)
    elastic_profile_balanced_render_citations: bool = _env_bool("MEMORY_PROFILE_BALANCED_RENDER_CITATIONS", False)
    elastic_profile_broad_lexical_k: int = _env_int("MEMORY_PROFILE_BROAD_LEXICAL_K", 96)
    elastic_profile_broad_vector_k: int = _env_int("MEMORY_PROFILE_BROAD_VECTOR_K", 96)
    elastic_profile_broad_num_candidates: int = _env_int("MEMORY_PROFILE_BROAD_NUM_CANDIDATES", 384)
    elastic_profile_broad_final_k: int = _env_int("MEMORY_PROFILE_BROAD_FINAL_K", 14)
    elastic_profile_broad_render_citations: bool = _env_bool("MEMORY_PROFILE_BROAD_RENDER_CITATIONS", False)


CFG = MemoryServiceConfig()


def memory_api_write_bearer_token() -> str:
    return _env_secret("MEMORY_API_WRITE_BEARER_TOKEN", "MEMORY_API_WRITE_BEARER_TOKEN_FILE")


def retrieval_profile(profile: str) -> dict[str, Any]:
    normalized = (profile or "balanced").strip().lower()
    if normalized == "precise":
        return {
            "profile": "precise",
            "lexical_k": CFG.elastic_profile_precise_lexical_k,
            "vector_k": CFG.elastic_profile_precise_vector_k,
            "num_candidates": CFG.elastic_profile_precise_num_candidates,
            "final_k": CFG.elastic_profile_precise_final_k,
            "render_citations": CFG.elastic_profile_precise_render_citations,
        }
    if normalized == "broad":
        return {
            "profile": "broad",
            "lexical_k": CFG.elastic_profile_broad_lexical_k,
            "vector_k": CFG.elastic_profile_broad_vector_k,
            "num_candidates": CFG.elastic_profile_broad_num_candidates,
            "final_k": CFG.elastic_profile_broad_final_k,
            "render_citations": CFG.elastic_profile_broad_render_citations,
        }
    return {
        "profile": "balanced",
        "lexical_k": CFG.elastic_profile_balanced_lexical_k,
        "vector_k": CFG.elastic_profile_balanced_vector_k,
        "num_candidates": CFG.elastic_profile_balanced_num_candidates,
        "final_k": CFG.elastic_profile_balanced_final_k,
        "render_citations": CFG.elastic_profile_balanced_render_citations,
    }
