"""Ports: what the domain and use cases need, never a library.

Tout fournisseur (LLM, embeddings, base vectorielle, stockage) se branche en
implementing one of these contracts, without touching the domain or use cases.
"""

from collections.abc import Iterator
from typing import Protocol

from app.domain.entities import Chunk, Document, ScoredChunk


class TextSplitter(Protocol):
    def split(self, text: str) -> list[str]: ...


class DocumentRepository(Protocol):
    """Source of truth for documents (full text): the vector store is only a rebuildable index."""

    def save(self, document: Document) -> None: ...

    def get(self, document_id: str) -> Document | None: ...

    def list(self) -> list[Document]: ...

    def delete(self, document_id: str) -> bool: ...


class VectorStore(Protocol):
    name: str  # provider name, for display

    def add_chunks(self, chunks: list[Chunk]) -> None: ...

    def delete_chunks(self, chunk_ids: list[str]) -> None: ...

    def search(self, query: str, k: int) -> list[ScoredChunk]: ...

    def clear(self) -> None: ...


class TextGenerator(Protocol):
    """The LLM as the application sees it: two operations, no SDK."""

    def stream_answer(self, question: str, passages: list[str]) -> Iterator[str]: ...

    def rewrite(self, question: str) -> str: ...
