import re
from collections.abc import Iterator

from app.domain.entities import Chunk, Document, ScoredChunk


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


class InMemoryVectorStore:
    """Test double of the VectorStore port: similarity = word overlap (0..1)."""

    name = "fake"

    def __init__(self) -> None:
        self.chunks: dict[str, Chunk] = {}

    def add_chunks(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self.chunks[c.id] = c

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        for i in chunk_ids:
            self.chunks.pop(i, None)

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        q = words(query)
        scored = [ScoredChunk(c, len(q & words(c.text)) / max(len(q), 1)) for c in self.chunks.values()]
        return sorted(scored, key=lambda s: s.score, reverse=True)[:k]

    def clear(self) -> None:
        self.chunks.clear()


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    def save(self, document: Document) -> None:
        self.documents[document.id] = document

    def get(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def list(self) -> list[Document]:
        return list(self.documents.values())

    def delete(self, document_id: str) -> bool:
        return self.documents.pop(document_id, None) is not None


class FakeGenerator:
    def __init__(self, rewrite_to: str | None = None) -> None:
        self.rewrite_to = rewrite_to
        self.rewrite_calls = 0

    def stream_answer(self, question: str, passages: list[str]) -> Iterator[str]:
        yield "answer"
        yield f"({len(passages)})"

    def rewrite(self, question: str) -> str:
        self.rewrite_calls += 1
        return self.rewrite_to or question


class LineSplitter:
    def split(self, text: str) -> list[str]:
        return text.split("\n")
