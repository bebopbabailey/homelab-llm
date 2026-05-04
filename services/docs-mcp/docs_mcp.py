#!/usr/bin/env python3
"""Studio-local MCP backend for curated document libraries backed by vector-db."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from html import unescape
from http import HTTPStatus
from pathlib import Path, PurePosixPath
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader
from starlette.applications import Starlette
from starlette.responses import JSONResponse

MCP_SERVER_NAME = "docs-mcp"
DEFAULT_VECTOR_DB_BASE = "http://127.0.0.1:55440"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8013
DEFAULT_MAX_FILE_MB = 50
DEFAULT_MAX_FILES_PER_INGEST = 10
DEFAULT_MAX_CHUNKS_PER_DOCUMENT = 500
DEFAULT_CHUNK_TARGET_CHARS = 300
DEFAULT_CHUNK_OVERLAP_CHARS = 40
DEFAULT_SEARCH_TOP_K = 5
MAX_SEARCH_TOP_K = 10
_WS_RE = re.compile(r"\s+")
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
_HTML_TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_HTML_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\\1>")
_HTML_TAG_RE = re.compile(r"(?is)<[^>]+>")
_SLUG_RE = re.compile(r"[^a-z0-9]+")

mcp = FastMCP(MCP_SERVER_NAME)
_HTTP_CLIENT: httpx.Client | None = None


class ToolContractError(RuntimeError):
    """Stable tool error with a machine-parseable code prefix."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class LibrarySpec:
    library_id: str
    library_handle: str
    title: str
    source_type: str
    root_path: Path
    supported_extensions: tuple[str, ...]


@dataclass(frozen=True)
class ServiceConfig:
    vector_db_base: str
    vector_db_write_token: str
    bearer_token: str
    max_file_mb: int
    max_files_per_ingest: int
    max_chunks_per_document: int
    chunk_target_chars: int
    chunk_overlap_chars: int
    libraries: tuple[LibrarySpec, ...]


@dataclass(frozen=True)
class IngestFile:
    path: Path
    relative_path: PurePosixPath
    document_handle: str
    source_uri: str
    extension: str
    title: str


@dataclass(frozen=True)
class ChunkRecord:
    text: str
    chunk_index: int
    section_title: str = ""
    page_start: int | None = None
    page_end: int | None = None
    char_start: int | None = None
    char_end: int | None = None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_secret(name: str, file_name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    file_path = os.getenv(file_name, "").strip()
    if not file_path:
        return ""
    try:
        return Path(file_path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _normalize_token(raw: str) -> str:
    token = (raw or "").strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    return token


def _music_manuals_root() -> Path:
    raw = os.getenv("DOCS_MCP_LIBRARY_MUSIC_MANUALS_ROOT", "/Users/thestudio/Documents/music-manuals").strip()
    return Path(raw).expanduser()


def _build_config() -> ServiceConfig:
    libraries = (
        LibrarySpec(
            library_id="music-manuals",
            library_handle="library:music-manuals",
            title="Music Manuals",
            source_type="manual",
            root_path=_music_manuals_root(),
            supported_extensions=(".pdf", ".txt", ".md", ".html", ".htm"),
        ),
    )
    return ServiceConfig(
        vector_db_base=os.getenv("DOCS_MCP_VECTOR_DB_BASE", DEFAULT_VECTOR_DB_BASE).rstrip("/"),
        vector_db_write_token=_env_secret("DOCS_MCP_VECTOR_DB_WRITE_TOKEN", "DOCS_MCP_VECTOR_DB_WRITE_TOKEN_FILE"),
        bearer_token=_normalize_token(_env_secret("DOCS_MCP_BEARER_TOKEN", "DOCS_MCP_BEARER_TOKEN_FILE")),
        max_file_mb=_env_int("DOCS_MCP_MAX_FILE_MB", DEFAULT_MAX_FILE_MB),
        max_files_per_ingest=_env_int("DOCS_MCP_MAX_FILES_PER_INGEST", DEFAULT_MAX_FILES_PER_INGEST),
        max_chunks_per_document=_env_int("DOCS_MCP_MAX_CHUNKS_PER_DOCUMENT", DEFAULT_MAX_CHUNKS_PER_DOCUMENT),
        chunk_target_chars=_env_int("DOCS_MCP_CHUNK_TARGET_CHARS", DEFAULT_CHUNK_TARGET_CHARS),
        chunk_overlap_chars=_env_int("DOCS_MCP_CHUNK_OVERLAP_CHARS", DEFAULT_CHUNK_OVERLAP_CHARS),
        libraries=libraries,
    )


CFG = _build_config()


def _build_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=5.0),
        follow_redirects=False,
        trust_env=False,
    )


def _get_http_client() -> httpx.Client:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = _build_client()
    return _HTTP_CLIENT


def _close_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None:
        _HTTP_CLIENT.close()
        _HTTP_CLIENT = None


atexit.register(_close_client)


def _collapse_ws(text: str) -> str:
    return _WS_RE.sub(" ", text or "").strip()


def _slugify(value: str) -> str:
    lowered = value.lower()
    normalized = _SLUG_RE.sub("-", lowered).strip("-")
    return normalized or "document"


def _relative_slug(relative_path: PurePosixPath) -> str:
    without_suffix = relative_path.with_suffix("")
    parts = [_slugify(part) for part in without_suffix.parts]
    return "--".join(part for part in parts if part) or "document"


def _content_hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _title_from_relative_path(relative_path: PurePosixPath) -> str:
    stem = relative_path.stem.replace("_", " ").replace("-", " ").strip()
    return stem or relative_path.name


def _make_source_uri(library: LibrarySpec, relative_path: PurePosixPath) -> str:
    return f"file://{library.library_handle}/{relative_path.as_posix()}"


def _validate_relative_path(text: str) -> PurePosixPath:
    raw = (text or "").strip()
    if not raw:
        raise ToolContractError("invalid_selector", "relative_path is required")
    if raw.startswith("/"):
        raise ToolContractError("invalid_selector", "relative_path must be relative to the library root")
    candidate = PurePosixPath(raw)
    if any(part == ".." for part in candidate.parts):
        raise ToolContractError("path_traversal_blocked", "relative_path may not escape the library root")
    if candidate == PurePosixPath("."):
        raise ToolContractError("invalid_selector", "relative_path may not be '.'")
    return candidate


def _resolve_library(library_id: str | None, library_handle: str | None, cfg: ServiceConfig = CFG) -> LibrarySpec:
    if bool(library_id) == bool(library_handle):
        raise ToolContractError("invalid_selector", "exactly one of library_id or library_handle is required")
    for library in cfg.libraries:
        if library_id and library.library_id == library_id:
            return library
        if library_handle and library.library_handle == library_handle:
            return library
    raise ToolContractError("unknown_library", "requested library is not registered")


def _resolve_inside_root(root: Path, relative_path: PurePosixPath) -> Path:
    root_resolved = root.resolve()
    candidate = (root / Path(relative_path)).resolve()
    if not str(candidate).startswith(str(root_resolved) + os.sep) and candidate != root_resolved:
        raise ToolContractError("path_traversal_blocked", "resolved path escapes the registered library root")
    return candidate


def _scan_library_files(library: LibrarySpec) -> list[Path]:
    if not library.root_path.exists():
        raise ToolContractError("library_root_missing", f"library root not found: {library.root_path}")
    return sorted(path for path in library.root_path.rglob("*") if path.is_file())


def _ingest_file_for_path(library: LibrarySpec, path: Path) -> IngestFile:
    relative = PurePosixPath(path.relative_to(library.root_path).as_posix())
    return IngestFile(
        path=path,
        relative_path=relative,
        document_handle=f"{library.source_type}:{library.library_id}:{_relative_slug(relative)}",
        source_uri=_make_source_uri(library, relative),
        extension=path.suffix.lower(),
        title=_title_from_relative_path(relative),
    )


def _resolve_document_handle(library: LibrarySpec, document_handle: str) -> IngestFile:
    target = (document_handle or "").strip()
    if not target:
        raise ToolContractError("invalid_selector", "document_handle is required")
    for path in _scan_library_files(library):
        ingest_file = _ingest_file_for_path(library, path)
        if ingest_file.document_handle == target:
            return ingest_file
    raise ToolContractError("unknown_document", f"document_handle not found in {library.library_handle}")


def _collect_ingest_files(
    library: LibrarySpec,
    *,
    document_handle: str | None,
    relative_path: str | None,
) -> tuple[list[IngestFile], list[dict[str, Any]], list[dict[str, Any]]]:
    if document_handle and relative_path:
        raise ToolContractError("invalid_selector", "choose document_handle or relative_path, not both")
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if document_handle:
        return [_resolve_document_handle(library, document_handle)], skipped, errors
    if relative_path:
        rel = _validate_relative_path(relative_path)
        path = _resolve_inside_root(library.root_path, rel)
        if not path.is_file():
            raise ToolContractError("unknown_document", f"relative_path not found: {relative_path}")
        return [_ingest_file_for_path(library, path)], skipped, errors

    files: list[IngestFile] = []
    for path in _scan_library_files(library):
        ingest_file = _ingest_file_for_path(library, path)
        if ingest_file.extension not in library.supported_extensions:
            skipped.append(
                {
                    "relative_path": ingest_file.relative_path.as_posix(),
                    "reason": f"unsupported_extension:{ingest_file.extension or '<none>'}",
                }
            )
            continue
        files.append(ingest_file)
    return files, skipped, errors


def _chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[tuple[str, int, int]]:
    clean = (text or "").strip()
    if not clean:
        return []
    if len(clean) <= max_chars:
        return [(clean, 0, len(clean))]
    out: list[tuple[str, int, int]] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + max_chars)
        chunk = clean[start:end].strip()
        if chunk:
            chunk_start = clean.find(chunk, start, end)
            chunk_end = chunk_start + len(chunk)
            out.append((chunk, chunk_start, chunk_end))
        if end >= len(clean):
            break
        start = max(0, end - overlap_chars)
    return out


def _read_pdf_chunks(path: Path, cfg: ServiceConfig = CFG) -> tuple[list[ChunkRecord], str]:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise ToolContractError("pdf_decrypt_failed", f"unable to decrypt PDF with empty password: {exc}") from exc
    chunks: list[ChunkRecord] = []
    full_text_parts: list[str] = []
    chunk_index = 0
    for page_number, page in enumerate(reader.pages, start=1):
        text = _collapse_ws(page.extract_text() or "")
        if not text:
            continue
        full_text_parts.append(text)
        for piece, char_start, char_end in _chunk_text(text, cfg.chunk_target_chars, cfg.chunk_overlap_chars):
            chunks.append(
                ChunkRecord(
                    text=piece,
                    chunk_index=chunk_index,
                    page_start=page_number,
                    page_end=page_number,
                    char_start=char_start,
                    char_end=char_end,
                )
            )
            chunk_index += 1
    return chunks, "\n".join(full_text_parts)


def _split_markdown_sections(text: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = _collapse_ws(match.group(2))
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines or current_heading:
        sections.append((current_heading, current_lines))
    if not sections:
        sections.append((None, [text]))
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections if "\n".join(lines).strip()]


def _read_text_like_chunks(path: Path, extension: str, cfg: ServiceConfig = CFG) -> tuple[list[ChunkRecord], str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    sections: list[tuple[str | None, str]]
    if extension in {".html", ".htm"}:
        title_match = _HTML_TITLE_RE.search(raw)
        html = _HTML_SCRIPT_STYLE_RE.sub(" ", raw)
        html = _HTML_TAG_RE.sub(" ", html)
        body = _collapse_ws(unescape(html))
        title = _collapse_ws(unescape(title_match.group(1))) if title_match else None
        sections = [(title, body)]
    elif extension == ".md":
        sections = _split_markdown_sections(raw)
    else:
        sections = [(None, raw)]

    chunks: list[ChunkRecord] = []
    full_text_parts: list[str] = []
    global_offset = 0
    chunk_index = 0
    for section_title, section_text in sections:
        clean = _collapse_ws(section_text)
        if not clean:
            continue
        full_text_parts.append(clean)
        for piece, local_start, local_end in _chunk_text(clean, cfg.chunk_target_chars, cfg.chunk_overlap_chars):
            chunks.append(
                ChunkRecord(
                    text=piece,
                    chunk_index=chunk_index,
                    section_title=section_title or "",
                    char_start=global_offset + local_start,
                    char_end=global_offset + local_end,
                )
            )
            chunk_index += 1
        global_offset += len(clean) + 1
    return chunks, "\n".join(full_text_parts)


def _extract_chunks(ingest_file: IngestFile, cfg: ServiceConfig = CFG) -> tuple[list[ChunkRecord], str]:
    if ingest_file.extension == ".pdf":
        return _read_pdf_chunks(ingest_file.path, cfg)
    if ingest_file.extension in {".txt", ".md", ".html", ".htm"}:
        return _read_text_like_chunks(ingest_file.path, ingest_file.extension, cfg)
    raise ToolContractError("unsupported_extension", f"unsupported extension: {ingest_file.extension}")


class VectorDBClient:
    def __init__(self, base_url: str, write_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.write_token = write_token

    def _headers(self, write: bool) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if write:
            if not self.write_token:
                raise ToolContractError("vector_db_auth_missing", "docs-mcp write token is not configured")
            headers["Authorization"] = f"Bearer {self.write_token}"
        return headers

    def upsert(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        response = _get_http_client().post(
            f"{self.base_url}/v1/memory/upsert",
            headers=self._headers(write=True),
            json={"documents": documents},
        )
        return _parse_json_response(response, "vector_db_upsert_failed")

    def delete_document(self, document_id: str) -> dict[str, Any]:
        response = _get_http_client().post(
            f"{self.base_url}/v1/memory/delete",
            headers=self._headers(write=True),
            json={"document_id": document_id},
        )
        return _parse_json_response(response, "vector_db_delete_failed")

    def search(
        self,
        *,
        query: str,
        document_id: str | None = None,
        source_type: str | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int = DEFAULT_SEARCH_TOP_K,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "profile": "balanced",
            "top_k": max(1, min(int(top_k), MAX_SEARCH_TOP_K)),
            "final_k": max(1, min(int(top_k), MAX_SEARCH_TOP_K)),
            "document_id": document_id,
            "source_type": source_type,
            "filters": filters or {},
        }
        response = _get_http_client().post(
            f"{self.base_url}/v1/memory/search",
            headers=self._headers(write=False),
            json=payload,
        )
        return _parse_json_response(response, "vector_db_search_failed")


def _parse_json_response(response: httpx.Response, error_code: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ToolContractError(error_code, f"non-JSON response from vector-db: {response.status_code}") from exc
    if response.status_code >= 400:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        raise ToolContractError(error_code, f"{response.status_code}: {detail}")
    if not isinstance(payload, dict):
        raise ToolContractError(error_code, "unexpected vector-db response shape")
    return payload


class DocsService:
    def __init__(self, cfg: ServiceConfig, vector_db: VectorDBClient) -> None:
        self.cfg = cfg
        self.vector_db = vector_db

    def list_libraries(self) -> dict[str, Any]:
        return {
            "libraries": [
                {
                    "library_id": lib.library_id,
                    "library_handle": lib.library_handle,
                    "title": lib.title,
                    "source_type": lib.source_type,
                    "supported_extensions": list(lib.supported_extensions),
                }
                for lib in self.cfg.libraries
            ]
        }

    def ingest_library(
        self,
        *,
        library_id: str | None,
        library_handle: str | None,
        document_handle: str | None = None,
        relative_path: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        library = _resolve_library(library_id, library_handle, self.cfg)
        ingest_files, skipped_files, errors = _collect_ingest_files(
            library,
            document_handle=document_handle,
            relative_path=relative_path,
        )
        if len(ingest_files) > self.cfg.max_files_per_ingest:
            raise ToolContractError(
                "ingest_limit_exceeded",
                f"matched {len(ingest_files)} files, above max_files_per_ingest={self.cfg.max_files_per_ingest}",
            )
        matched_files = [item.relative_path.as_posix() for item in ingest_files]
        previews = [
            {
                "relative_path": item.relative_path.as_posix(),
                "document_handle": item.document_handle,
                "source_uri": item.source_uri,
            }
            for item in ingest_files
        ]
        if dry_run:
            would_index = 0
            for item in ingest_files:
                try:
                    self._validate_file_size(item)
                    if item.extension not in library.supported_extensions:
                        skipped_files.append(
                            {
                                "relative_path": item.relative_path.as_posix(),
                                "reason": f"unsupported_extension:{item.extension}",
                            }
                        )
                    else:
                        would_index += 1
                except ToolContractError as exc:
                    errors.append(
                        {
                            "relative_path": item.relative_path.as_posix(),
                            "code": exc.code,
                            "message": exc.message,
                        }
                    )
            return {
                "library_handle": library.library_handle,
                "matched_files": matched_files,
                "would_index": would_index,
                "would_skip": skipped_files,
                "document_handle_previews": previews,
                "errors": errors,
                "dry_run": True,
            }

        ingest_run_id = f"INGEST-{uuid.uuid4().hex[:12]}"
        documents_indexed = 0
        chunks_indexed = 0
        indexed_handles: list[str] = []
        for item in ingest_files:
            try:
                self._validate_file_size(item)
                if item.extension not in library.supported_extensions:
                    skipped_files.append(
                        {
                            "relative_path": item.relative_path.as_posix(),
                            "reason": f"unsupported_extension:{item.extension}",
                        }
                    )
                    continue
                payload, chunk_count = self._build_document_payload(library, item, ingest_run_id)
                self.vector_db.delete_document(item.document_handle)
                self.vector_db.upsert([payload])
                documents_indexed += 1
                chunks_indexed += chunk_count
                indexed_handles.append(item.document_handle)
            except ToolContractError as exc:
                errors.append(
                    {
                        "relative_path": item.relative_path.as_posix(),
                        "code": exc.code,
                        "message": exc.message,
                    }
                )
        return {
            "library_handle": library.library_handle,
            "document_handles": indexed_handles,
            "documents_indexed": documents_indexed,
            "chunks_indexed": chunks_indexed,
            "skipped_files": skipped_files,
            "errors": errors,
            "ingest_run_id": ingest_run_id,
            "dry_run": False,
        }

    def search_library(self, *, library_id: str | None, library_handle: str | None, query: str, top_k: int = DEFAULT_SEARCH_TOP_K) -> dict[str, Any]:
        library = _resolve_library(library_id, library_handle, self.cfg)
        ingest_files, _skipped_files, _errors = _collect_ingest_files(
            library,
            document_handle=None,
            relative_path=None,
        )
        hits: list[dict[str, Any]] = []
        for item in ingest_files[: self.cfg.max_files_per_ingest]:
            response = self.vector_db.search(
                query=query,
                document_id=item.document_handle,
                top_k=top_k,
            )
            hits.extend(response.get("hits", []))
        hits.sort(
            key=lambda item: (
                float(item.get("rrf_score", 0.0) or 0.0),
                -int(item.get("rank", 0) or 0),
            ),
            reverse=True,
        )
        return {
            "query": query,
            "library_handle": library.library_handle,
            "hits": [_normalize_hit(hit) for hit in hits[: max(1, min(int(top_k), MAX_SEARCH_TOP_K))]],
        }

    def search_document(self, *, document_handle: str, query: str, top_k: int = DEFAULT_SEARCH_TOP_K) -> dict[str, Any]:
        handle = (document_handle or "").strip()
        if not handle:
            raise ToolContractError("invalid_selector", "document_handle is required")
        response = self.vector_db.search(query=query, document_id=handle, top_k=top_k)
        return {
            "query": query,
            "document_handle": handle,
            "hits": [_normalize_hit(hit) for hit in response.get("hits", [])],
        }

    def _validate_file_size(self, ingest_file: IngestFile) -> None:
        size_bytes = ingest_file.path.stat().st_size
        if size_bytes > self.cfg.max_file_mb * 1024 * 1024:
            raise ToolContractError(
                "file_too_large",
                f"{ingest_file.relative_path.as_posix()} exceeds max_file_mb={self.cfg.max_file_mb}",
            )

    def _build_document_payload(self, library: LibrarySpec, ingest_file: IngestFile, ingest_run_id: str) -> tuple[dict[str, Any], int]:
        raw_bytes = ingest_file.path.read_bytes()
        content_hash = _content_hash_bytes(raw_bytes)
        chunks, _full_text = _extract_chunks(ingest_file, self.cfg)
        if not chunks:
            raise ToolContractError("empty_document", f"no extractable text for {ingest_file.relative_path.as_posix()}")
        if len(chunks) > self.cfg.max_chunks_per_document:
            raise ToolContractError(
                "chunk_limit_exceeded",
                f"{ingest_file.relative_path.as_posix()} produced {len(chunks)} chunks, above max_chunks_per_document={self.cfg.max_chunks_per_document}",
            )
        payload_chunks = []
        for chunk in chunks:
            chunk_meta = {
                "relative_path": ingest_file.relative_path.as_posix(),
                "content_hash": content_hash,
                "ingest_run_id": ingest_run_id,
                "library_id": library.library_id,
                "library_handle": library.library_handle,
                "document_handle": ingest_file.document_handle,
            }
            payload_chunks.append(
                {
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "section_title": chunk.section_title or "",
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "metadata": chunk_meta,
                }
            )
        payload = {
            "document_id": ingest_file.document_handle,
            "source_type": library.source_type,
            "source": "docs-mcp",
            "title": ingest_file.title,
            "uri": ingest_file.source_uri,
            "metadata": {
                "library_id": library.library_id,
                "library_handle": library.library_handle,
                "document_handle": ingest_file.document_handle,
                "relative_path": ingest_file.relative_path.as_posix(),
                "content_hash": content_hash,
                "ingest_run_id": ingest_run_id,
            },
            "chunks": payload_chunks,
        }
        return payload, len(payload_chunks)


def _normalize_hit(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": hit.get("document_id"),
        "document_handle": hit.get("document_id"),
        "title": hit.get("title"),
        "text": hit.get("text"),
        "spans": hit.get("spans", {}),
        "score": hit.get("rrf_score"),
        "rank": hit.get("rank"),
    }


SERVICE = DocsService(CFG, VectorDBClient(CFG.vector_db_base, CFG.vector_db_write_token))


class BearerAuthMiddleware:
    def __init__(self, app: Starlette, *, bearer_token: str) -> None:
        self.app = app
        self._bearer_token = _normalize_token(bearer_token)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if not self._bearer_token:
            response = JSONResponse(
                {
                    "error": "config_error",
                    "message": "docs-mcp bearer token is not configured",
                },
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            await response(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        authorization = headers.get("authorization", "").strip()
        if not authorization.startswith("Bearer "):
            response = JSONResponse(
                {
                    "error": "unauthorized",
                    "message": "missing bearer token",
                },
                status_code=HTTPStatus.UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        actual = _normalize_token(authorization)
        if actual != self._bearer_token:
            response = JSONResponse(
                {
                    "error": "unauthorized",
                    "message": "invalid bearer token",
                },
                status_code=HTTPStatus.FORBIDDEN,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


@mcp.tool(name="docs.library.list")
def docs_library_list() -> dict[str, Any]:
    """List registered curated document libraries."""

    return SERVICE.list_libraries()


@mcp.tool(name="docs.library.ingest")
def docs_library_ingest(
    library_id: str | None = None,
    library_handle: str | None = None,
    document_handle: str | None = None,
    relative_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ingest one registered library or one file within it into vector-db."""

    return SERVICE.ingest_library(
        library_id=library_id,
        library_handle=library_handle,
        document_handle=document_handle,
        relative_path=relative_path,
        dry_run=bool(dry_run),
    )


@mcp.tool(name="docs.library.search")
def docs_library_search(
    query: str,
    library_id: str | None = None,
    library_handle: str | None = None,
    top_k: int = DEFAULT_SEARCH_TOP_K,
) -> dict[str, Any]:
    """Search one explicit registered library and return evidence only."""

    return SERVICE.search_library(
        library_id=library_id,
        library_handle=library_handle,
        query=query,
        top_k=top_k,
    )


@mcp.tool(name="docs.document.search")
def docs_document_search(document_handle: str, query: str, top_k: int = DEFAULT_SEARCH_TOP_K) -> dict[str, Any]:
    """Search one explicit document and return evidence only."""

    return SERVICE.search_document(document_handle=document_handle, query=query, top_k=top_k)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the docs-mcp server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.transport == "streamable-http":
        import uvicorn

        mcp.settings.host = args.host
        mcp.settings.port = args.port
        host_pattern = f"{args.host}:*"
        origin_pattern = f"http://{args.host}:*"
        security = mcp.settings.transport_security
        if host_pattern not in security.allowed_hosts:
            security.allowed_hosts.append(host_pattern)
        if origin_pattern not in security.allowed_origins:
            security.allowed_origins.append(origin_pattern)
        app = mcp.streamable_http_app()
        app.add_middleware(BearerAuthMiddleware, bearer_token=CFG.bearer_token)
        config = uvicorn.Config(
            app,
            host=args.host,
            port=args.port,
            log_level=mcp.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        server.run()
        return
    mcp.run(args.transport)


if __name__ == "__main__":
    main()
