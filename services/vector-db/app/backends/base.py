from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SearchArgs:
    query: str
    top_k: int
    lexical_k: int
    vector_k: int
    model_space: str


class MemoryBackend(Protocol):
    def health(self) -> dict[str, Any]: ...

    def stats(self) -> dict[str, Any]: ...

    def upsert(self, documents: list[dict[str, Any]]) -> dict[str, int]: ...

    def search(self, args: SearchArgs) -> list[dict[str, Any]]: ...

    def delete(self, source: str) -> int: ...
