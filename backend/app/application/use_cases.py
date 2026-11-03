import hashlib
import logging
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, replace

from app.application.ports import RagWorkflow
from app.domain.entities import Answer, Chunk, Document, DoneEvent, StreamEvent, chunk_ids
from app.domain.errors import DocumentNotFoundError, EmptyDocumentError, EmptyQuestionError
from app.domain.ports import DocumentRepository, TextSplitter, VectorStore

log = logging.getLogger("rag.admin")


def document_id_for(source: str) -> str:
    """Stable identifier: re-ingesting the same file replaces the document."""
    base = unicodedata.normalize("NFKD", source).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "document"
    return f"{slug}-{hashlib.sha1(source.encode()).hexdigest()[:6]}"


class Indexer:
    """Splits a document and updates the index (removes old passages, adds new ones)."""

    def __init__(self, splitter: TextSplitter, store: VectorStore, repository: DocumentRepository) -> None:
        self._splitter = splitter
        self._store = store
        self._repository = repository

    def index(self, document: Document) -> Document:
        pieces = [p.strip() for p in self._splitter.split(document.text) if p.strip()]
        if not pieces:
            raise EmptyDocumentError()
        previous = self._repository.get(document.id)
        if previous:
            self._store.delete_chunks(chunk_ids(previous))
        indexed = replace(document, chunk_count=len(pieces))
        self._store.add_chunks(
            [Chunk(f"{indexed.id}:{i}", indexed.id, piece, indexed.source) for i, piece in enumerate(pieces)]
        )
        self._repository.save(indexed)
        return indexed


class IngestDocument:
    """Adds a document, or replaces the one with the same name."""

    def __init__(self, indexer: Indexer) -> None:
        self._indexer = indexer

    def __call__(self, source: str, text: str) -> Document:
        return self._indexer.index(Document(id=document_id_for(source), source=source, text=text))


class UpdateDocument:
    """Edits the text (and/or name) of an existing document and re-indexes its passages."""

    def __init__(self, indexer: Indexer, repository: DocumentRepository) -> None:
        self._indexer = indexer
        self._repository = repository

    def __call__(self, document_id: str, text: str, source: str | None = None) -> Document:
        current = self._repository.get(document_id)
        if current is None:
            raise DocumentNotFoundError()
        return self._indexer.index(replace(current, text=text, source=source or current.source))


class GetDocument:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    def __call__(self, document_id: str) -> Document:
        document = self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()
        return document


class ListDocuments:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    def __call__(self) -> list[Document]:
        return sorted(self._repository.list(), key=lambda d: d.source.lower())


class DeleteDocument:
    def __init__(self, repository: DocumentRepository, store: VectorStore) -> None:
        self._repository = repository
        self._store = store

    def __call__(self, document_id: str) -> None:
        document = self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()
        self._store.delete_chunks(chunk_ids(document))
        self._repository.delete(document_id)


@dataclass(frozen=True)
class VectorStoreInfo:
    provider: str
    embeddings: str
    llm: str
    documents: int
    chunks: int


class DescribeVectorStore:
    def __init__(self, repository: DocumentRepository, store: VectorStore, embeddings: str, llm: str) -> None:
        self._repository = repository
        self._store = store
        self._embeddings = embeddings
        self._llm = llm

    def __call__(self) -> VectorStoreInfo:
        documents = self._repository.list()
        return VectorStoreInfo(
            provider=self._store.name,
            embeddings=self._embeddings,
            llm=self._llm,
            documents=len(documents),
            chunks=sum(d.chunk_count for d in documents),
        )


class ClearVectorStore:
    """Empties the index: documents are kept and can be re-indexed."""

    def __init__(self, repository: DocumentRepository, store: VectorStore) -> None:
        self._repository = repository
        self._store = store

    def __call__(self) -> None:
        self._store.clear()
        for document in self._repository.list():
            self._repository.save(replace(document, chunk_count=0))
        log.info("vector store cleared", extra={"event": "vector_store.cleared"})


class ReindexAll:
    """Rebuilds the index from the documents: after a change of embedding model or store."""

    def __init__(self, indexer: Indexer, repository: DocumentRepository, store: VectorStore) -> None:
        self._indexer = indexer
        self._repository = repository
        self._store = store

    def __call__(self) -> tuple[int, int]:
        documents = self._repository.list()
        self._store.clear()
        chunks = 0
        for document in documents:
            # the store was just emptied: no old passages left to remove
            self._repository.save(replace(document, chunk_count=0))
            chunks += self._indexer.index(document).chunk_count
        log.info("vector store reindexed", extra={"event": "vector_store.reindexed", "found": len(documents), "kept": chunks})
        return len(documents), chunks


class AskQuestion:
    def __init__(self, workflow: RagWorkflow) -> None:
        self._workflow = workflow

    def stream(self, question: str) -> Iterator[StreamEvent]:
        """Validates eagerly (not lazily on the first event), so callers can fail before opening a stream."""
        cleaned = question.strip()
        if not cleaned:
            raise EmptyQuestionError()
        return self._workflow.stream(cleaned)

    def __call__(self, question: str) -> Answer:
        """Non-streaming variant: consumes the stream and returns the final answer."""
        for event in self.stream(question):
            if isinstance(event, DoneEvent):
                return event.answer
        raise RuntimeError("the workflow ended without an answer")
