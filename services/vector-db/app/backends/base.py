from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SearchArgs:
    query: str
    top_k: int
    lexical_k: int
    vector_k: int
    num_candidates: int
    final_k: int
    model_space: str
    profile: str
    document_id: str | None = None
    source_type: str | None = None
    source_types: tuple[str, ...] = ()
    render_citations: bool = False
    filters: dict[str, Any] | None = None
    vector_search_mode: str = "auto"


class MemoryBackend(Protocol):
    def health(self) -> dict[str, Any]: ...

    def stats(self) -> dict[str, Any]: ...

    def upsert(self, documents: list[dict[str, Any]]) -> dict[str, int]: ...

    def search(self, args: SearchArgs) -> list[dict[str, Any]]: ...

    def delete(self, source: str | None = None, document_id: str | None = None) -> int: ...

    def upsert_response_mapping(
        self,
        *,
        response_id: str,
        document_id: str,
        source_type: str,
        summary_mode: str,
    ) -> dict[str, Any]: ...

    def resolve_response_mapping(self, response_id: str) -> dict[str, Any] | None: ...
