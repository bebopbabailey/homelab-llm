from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass(frozen=True)
class EmbedModelConfig:
    model_id: str
    hf_repo: str
    default_dimension: int
    query_prefix: str = ""
    document_prefix: str = ""
    prefix_mode: str = "raw"
    trust_remote_code: bool = False


MODEL_MAP = {
    "studio-nomic-embed-text-v1.5": EmbedModelConfig(
        model_id="studio-nomic-embed-text-v1.5",
        hf_repo=os.getenv("MEMORY_EMBED_NOMIC_REPO", "nomic-ai/nomic-embed-text-v1.5"),
        default_dimension=int(os.getenv("MEMORY_EMBED_NOMIC_DIM", "768")),
        query_prefix=os.getenv("MEMORY_EMBED_NOMIC_QUERY_PREFIX", "search_query:"),
        document_prefix=os.getenv("MEMORY_EMBED_NOMIC_DOCUMENT_PREFIX", "search_document:"),
        prefix_mode="search_query/search_document",
        trust_remote_code=True,
    ),
    "studio-qwen-embed-0.6b": EmbedModelConfig(
        model_id="studio-qwen-embed-0.6b",
        hf_repo=os.getenv("MEMORY_EMBED_QWEN_REPO", "Qwen/Qwen3-Embedding-0.6B"),
        default_dimension=int(os.getenv("MEMORY_EMBED_QWEN_DIM", "1024")),
    ),
    "studio-mxbai-embed-large-v1": EmbedModelConfig(
        model_id="studio-mxbai-embed-large-v1",
        hf_repo=os.getenv("MEMORY_EMBED_MXBAI_REPO", "mixedbread-ai/mxbai-embed-large-v1"),
        default_dimension=int(os.getenv("MEMORY_EMBED_MXBAI_DIM", "1024")),
    ),
}


class EmbeddingRegistry:
    """Lazy model loader for embedding spaces."""

    def __init__(self) -> None:
        self._loaded: dict[str, SentenceTransformer] = {}

    def _load(self, model_name: str) -> SentenceTransformer:
        cfg = MODEL_MAP.get(model_name)
        if cfg is None:
            raise ValueError(f"unknown embedding model: {model_name}")
        if model_name not in self._loaded:
            self._loaded[model_name] = SentenceTransformer(
                cfg.hf_repo,
                trust_remote_code=cfg.trust_remote_code,
            )
        return self._loaded[model_name]

    def model_config(self, model_name: str) -> EmbedModelConfig:
        cfg = MODEL_MAP.get(model_name)
        if cfg is None:
            raise ValueError(f"unknown embedding model: {model_name}")
        return cfg

    def model_info(self, model_name: str) -> dict[str, str | int]:
        cfg = self.model_config(model_name)
        return {
            "model_id": cfg.model_id,
            "hf_repo": cfg.hf_repo,
            "default_dimension": cfg.default_dimension,
            "query_prefix": cfg.query_prefix,
            "document_prefix": cfg.document_prefix,
            "prefix_mode": cfg.prefix_mode,
            "trust_remote_code": cfg.trust_remote_code,
        }

    def embed(self, model_name: str, texts: Iterable[str]) -> list[list[float]]:
        model = self._load(model_name)
        vectors = model.encode(list(texts), normalize_embeddings=True)
        arr = np.asarray(vectors, dtype=np.float32)
        return arr.tolist()

    def embed_query(self, model_name: str, texts: Iterable[str]) -> list[list[float]]:
        cfg = self.model_config(model_name)
        prepared = [f"{cfg.query_prefix} {text}".strip() if cfg.query_prefix else str(text) for text in texts]
        return self.embed(model_name, prepared)

    def embed_document(self, model_name: str, texts: Iterable[str]) -> list[list[float]]:
        cfg = self.model_config(model_name)
        prepared = [f"{cfg.document_prefix} {text}".strip() if cfg.document_prefix else str(text) for text in texts]
        return self.embed(model_name, prepared)


def default_model() -> str:
    return os.getenv("MEMORY_EMBED_PRIMARY", "studio-nomic-embed-text-v1.5")


def fallback_model() -> str:
    return os.getenv("MEMORY_EMBED_FALLBACK", "studio-mxbai-embed-large-v1")
