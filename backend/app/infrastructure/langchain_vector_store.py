from collections.abc import Callable

from langchain_core.vectorstores import VectorStore as LangChainStore

from app.domain.entities import Chunk, ScoredChunk


class LangChainVectorStore:
    """Adapter of the VectorStore port for ANY LangChain vector store.

    `factory` creates a fresh (empty) store: this is what lets `clear()` work without knowing the store.
    """

    def __init__(self, name: str, factory: Callable[[], LangChainStore]) -> None:
        self.name = name
        self._factory = factory
        self._store = factory()

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self._store.add_texts(
            texts=[c.text for c in chunks],
            metadatas=[{"document_id": c.document_id, "source": c.source} for c in chunks],
            ids=[c.id for c in chunks],
        )

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        if chunk_ids:
            self._store.delete(ids=chunk_ids)

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        try:
            results = self._store.similarity_search_with_relevance_scores(query, k=k)
        except NotImplementedError:  # some stores do not normalise their score
            results = self._store.similarity_search_with_score(query, k=k)
        found: list[ScoredChunk] = []
        for doc, score in results:
            meta = doc.metadata or {}
            chunk = Chunk(
                id=str(doc.id or ""),
                document_id=str(meta.get("document_id", "")),
                text=doc.page_content,
                source=str(meta.get("source", "")),
            )
            found.append(ScoredChunk(chunk=chunk, score=max(0.0, min(1.0, float(score)))))
        return sorted(found, key=lambda s: s.score, reverse=True)

    def clear(self) -> None:
        delete_collection = getattr(self._store, "delete_collection", None)
        if callable(delete_collection):
            delete_collection()
        self._store = self._factory()
