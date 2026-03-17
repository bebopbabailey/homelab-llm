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


MODEL_MAP = {
    "studio-qwen-embed-0.6b": EmbedModelConfig(
        model_id="studio-qwen-embed-0.6b",
        hf_repo=os.getenv("MEMORY_EMBED_QWEN_REPO", "Qwen/Qwen3-Embedding-0.6B"),
    ),
    "studio-mxbai-embed-large-v1": EmbedModelConfig(
        model_id="studio-mxbai-embed-large-v1",
        hf_repo=os.getenv("MEMORY_EMBED_MXBAI_REPO", "mixedbread-ai/mxbai-embed-large-v1"),
    ),
}


class EmbeddingRegistry:
    """Lazy model loader for dual embedding spaces."""

    def __init__(self) -> None:
        self._loaded: dict[str, SentenceTransformer] = {}

    def _load(self, model_name: str) -> SentenceTransformer:
        cfg = MODEL_MAP.get(model_name)
        if cfg is None:
            raise ValueError(f"unknown embedding model: {model_name}")
        if model_name not in self._loaded:
            self._loaded[model_name] = SentenceTransformer(cfg.hf_repo)
        return self._loaded[model_name]

    def embed(self, model_name: str, texts: Iterable[str]) -> list[list[float]]:
        model = self._load(model_name)
        vectors = model.encode(list(texts), normalize_embeddings=True)
        arr = np.asarray(vectors, dtype=np.float32)
        return arr.tolist()


def default_model() -> str:
    return os.getenv("MEMORY_EMBED_PRIMARY", "studio-qwen-embed-0.6b")


def fallback_model() -> str:
    return os.getenv("MEMORY_EMBED_FALLBACK", "studio-mxbai-embed-large-v1")
