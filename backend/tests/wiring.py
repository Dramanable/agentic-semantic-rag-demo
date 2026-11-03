from app.application.use_cases import (
    AskQuestion,
    ClearVectorStore,
    DeleteDocument,
    DescribeVectorStore,
    GetDocument,
    Indexer,
    IngestDocument,
    ListDocuments,
    ReindexAll,
    UpdateDocument,
)
from app.infrastructure.container import Container
from app.infrastructure.rag_graph import LangGraphRagWorkflow
from tests.fakes import FakeGenerator, InMemoryDocumentRepository, InMemoryVectorStore, LineSplitter


def build_test_container(generator: FakeGenerator | None = None):
    """The same wiring as production, with in-memory doubles."""
    store, repo = InMemoryVectorStore(), InMemoryDocumentRepository()
    indexer = Indexer(LineSplitter(), store, repo)
    container = Container(
        ingest=IngestDocument(indexer),
        update=UpdateDocument(indexer, repo),
        get_document=GetDocument(repo),
        list_documents=ListDocuments(repo),
        delete=DeleteDocument(repo, store),
        ask=AskQuestion(LangGraphRagWorkflow(store, generator or FakeGenerator(), 3, 0.5, 1)),
        describe_store=DescribeVectorStore(repo, store, "fake-embeddings", "fake-llm"),
        clear_store=ClearVectorStore(repo, store),
        reindex=ReindexAll(indexer, repo, store),
    )
    return container, store, repo
