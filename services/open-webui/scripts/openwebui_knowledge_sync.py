#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() == "true"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class KnowledgeRuntimeConfig:
    embedding_engine: str
    embedding_model: str
    embedding_batch_size: int
    embedding_concurrent_requests: int
    enable_async_embedding: bool
    openai_base_url: str
    openai_api_key: str
    top_k: int
    rag_full_context: bool
    enable_hybrid_search: bool
    enable_hybrid_search_enriched_texts: bool
    relevance_threshold: float
    chunk_size: int
    chunk_overlap: int


def desired_runtime_config(env: dict[str, str] | None = None) -> KnowledgeRuntimeConfig:
    source = os.environ if env is None else env
    getenv = source.get
    return KnowledgeRuntimeConfig(
        embedding_engine=getenv("RAG_EMBEDDING_ENGINE", "openai"),
        embedding_model=getenv("RAG_EMBEDDING_MODEL", "studio-nomic-embed-text-v1.5"),
        embedding_batch_size=int(getenv("RAG_EMBEDDING_BATCH_SIZE", "1")),
        embedding_concurrent_requests=int(getenv("RAG_EMBEDDING_CONCURRENT_REQUESTS", "0")),
        enable_async_embedding=getenv("ENABLE_ASYNC_EMBEDDING", "true").strip().lower() == "true",
        openai_base_url=getenv("RAG_OPENAI_API_BASE_URL", "http://192.168.1.72:55440/v1"),
        openai_api_key=getenv("RAG_OPENAI_API_KEY", ""),
        top_k=int(getenv("RAG_TOP_K", "5")),
        rag_full_context=getenv("RAG_FULL_CONTEXT", "false").strip().lower() == "true",
        enable_hybrid_search=getenv("ENABLE_RAG_HYBRID_SEARCH", "true").strip().lower() == "true",
        enable_hybrid_search_enriched_texts=getenv("ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS", "true").strip().lower() == "true",
        relevance_threshold=float(getenv("RAG_RELEVANCE_THRESHOLD", "0.0")),
        chunk_size=int(getenv("CHUNK_SIZE", "1000")),
        chunk_overlap=int(getenv("CHUNK_OVERLAP", "100")),
    )


def build_embedding_payload(cfg: KnowledgeRuntimeConfig) -> dict[str, Any]:
    return {
        "RAG_EMBEDDING_ENGINE": cfg.embedding_engine,
        "RAG_EMBEDDING_MODEL": cfg.embedding_model,
        "RAG_EMBEDDING_BATCH_SIZE": cfg.embedding_batch_size,
        "ENABLE_ASYNC_EMBEDDING": cfg.enable_async_embedding,
        "RAG_EMBEDDING_CONCURRENT_REQUESTS": cfg.embedding_concurrent_requests,
        "openai_config": {
            "url": cfg.openai_base_url,
            "key": cfg.openai_api_key,
        },
    }


def build_rag_payload(cfg: KnowledgeRuntimeConfig) -> dict[str, Any]:
    return {
        "TOP_K": cfg.top_k,
        "RAG_FULL_CONTEXT": cfg.rag_full_context,
        "ENABLE_RAG_HYBRID_SEARCH": cfg.enable_hybrid_search,
        "ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS": cfg.enable_hybrid_search_enriched_texts,
        "RELEVANCE_THRESHOLD": cfg.relevance_threshold,
        "CHUNK_SIZE": cfg.chunk_size,
        "CHUNK_OVERLAP": cfg.chunk_overlap,
    }


def embedding_config_matches(current: dict[str, Any], desired: dict[str, Any]) -> bool:
    return (
        current.get("RAG_EMBEDDING_ENGINE") == desired["RAG_EMBEDDING_ENGINE"]
        and current.get("RAG_EMBEDDING_MODEL") == desired["RAG_EMBEDDING_MODEL"]
        and current.get("RAG_EMBEDDING_BATCH_SIZE") == desired["RAG_EMBEDDING_BATCH_SIZE"]
        and current.get("ENABLE_ASYNC_EMBEDDING") == desired["ENABLE_ASYNC_EMBEDDING"]
        and current.get("RAG_EMBEDDING_CONCURRENT_REQUESTS") == desired["RAG_EMBEDDING_CONCURRENT_REQUESTS"]
        and current.get("openai_config", {}).get("url") == desired["openai_config"]["url"]
        and current.get("openai_config", {}).get("key") == desired["openai_config"]["key"]
    )


def rag_config_matches(current: dict[str, Any], desired: dict[str, Any]) -> bool:
    return (
        current.get("TOP_K") == desired["TOP_K"]
        and current.get("RAG_FULL_CONTEXT") == desired["RAG_FULL_CONTEXT"]
        and current.get("ENABLE_RAG_HYBRID_SEARCH") == desired["ENABLE_RAG_HYBRID_SEARCH"]
        and current.get("ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS") == desired["ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS"]
        and float(current.get("RELEVANCE_THRESHOLD")) == desired["RELEVANCE_THRESHOLD"]
        and current.get("CHUNK_SIZE") == desired["CHUNK_SIZE"]
        and current.get("CHUNK_OVERLAP") == desired["CHUNK_OVERLAP"]
    )


def load_admin_api_key(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("select key from api_key order by created_at asc limit 1").fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        raise RuntimeError(f"no admin api key found in {db_path}")
    return str(row[0])


class OpenWebUIAdminClient:
    def __init__(self, base_url: str, bearer_token: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }

    def request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            headers=self.headers,
            data=data,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_embedding_config(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/v1/retrieval/embedding")

    def update_embedding_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request_json("POST", "/api/v1/retrieval/embedding/update", payload)

    def get_rag_config(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/v1/retrieval/config")

    def update_rag_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request_json("POST", "/api/v1/retrieval/config/update", payload)


def wait_for_health(base_url: str, timeout: float) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url.rstrip('/')}/health", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") is True:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"open-webui health check did not succeed within {timeout}s: {last_error}")


def sync_runtime(base_url: str, db_path: Path, timeout: float, apply_updates: bool) -> dict[str, Any]:
    wait_for_health(base_url, timeout)
    cfg = desired_runtime_config()
    desired_embedding = build_embedding_payload(cfg)
    desired_rag = build_rag_payload(cfg)
    client = OpenWebUIAdminClient(base_url, load_admin_api_key(db_path), timeout=10)

    current_embedding = client.get_embedding_config()
    current_rag = client.get_rag_config()
    embedding_changed = not embedding_config_matches(current_embedding, desired_embedding)
    rag_changed = not rag_config_matches(current_rag, desired_rag)

    if apply_updates and embedding_changed:
        current_embedding = client.update_embedding_config(desired_embedding)
        embedding_changed = not embedding_config_matches(current_embedding, desired_embedding)
    if apply_updates and rag_changed:
        current_rag = client.update_rag_config(desired_rag)
        rag_changed = not rag_config_matches(current_rag, desired_rag)

    result = {
        "ok": not embedding_changed and not rag_changed,
        "apply_updates": apply_updates,
        "embedding_changed": embedding_changed,
        "rag_changed": rag_changed,
        "desired_embedding": desired_embedding,
        "desired_rag": desired_rag,
        "current_embedding": current_embedding,
        "current_rag": current_rag,
        "env_only": {
            "VECTOR_DB": os.getenv("VECTOR_DB", ""),
            "ELASTICSEARCH_URL": os.getenv("ELASTICSEARCH_URL", ""),
            "ELASTICSEARCH_INDEX_PREFIX": os.getenv("ELASTICSEARCH_INDEX_PREFIX", ""),
            "RAG_EMBEDDING_PREFIX_FIELD_NAME": os.getenv("RAG_EMBEDDING_PREFIX_FIELD_NAME", ""),
            "RAG_EMBEDDING_QUERY_PREFIX": os.getenv("RAG_EMBEDDING_QUERY_PREFIX", ""),
            "RAG_EMBEDDING_CONTENT_PREFIX": os.getenv("RAG_EMBEDDING_CONTENT_PREFIX", ""),
        },
    }
    if not result["ok"]:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile Open WebUI retrieval config to backend-canonical env.")
    parser.add_argument("--base-url", default=os.getenv("OPENWEBUI_BASE_URL", "http://127.0.0.1:3000"))
    parser.add_argument("--db-path", default=os.getenv("OPENWEBUI_DB_PATH", "/home/christopherbailey/.open-webui/webui.db"))
    parser.add_argument("--health-timeout", type=float, default=_env_float("OPENWEBUI_SYNC_HEALTH_TIMEOUT", 60.0))
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = sync_runtime(
        base_url=args.base_url,
        db_path=Path(args.db_path),
        timeout=args.health_timeout,
        apply_updates=not args.check_only,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
