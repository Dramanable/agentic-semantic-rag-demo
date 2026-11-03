"""Composition root: the only place that knows the concrete adapters."""

from dataclasses import dataclass

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
from app.infrastructure.json_document_repository import JsonDocumentRepository
from app.infrastructure.providers.embeddings import embeddings_providers
from app.infrastructure.providers.llm import llm_providers
from app.infrastructure.providers.vector_stores import vector_store_providers
from app.infrastructure.rag_graph import LangGraphRagWorkflow
from app.infrastructure.settings import Settings
from app.infrastructure.splitter import LangChainTextSplitter


@dataclass
class Container:
    ingest: IngestDocument
    update: UpdateDocument
    get_document: GetDocument
    list_documents: ListDocuments
    delete: DeleteDocument
    ask: AskQuestion
    describe_store: DescribeVectorStore
    clear_store: ClearVectorStore
    reindex: ReindexAll


def _label(provider: str, model: str) -> str:
    return f"{provider} ({model})" if model else provider


def build_container(settings: Settings) -> Container:
    embeddings = embeddings_providers.build(settings.embeddings_provider, settings)
    store = vector_store_providers.build(settings.vector_store_provider, settings, embeddings)
    generator = llm_providers.build(settings.llm_provider, settings)
    repository = JsonDocumentRepository(settings.documents_path)
    splitter = LangChainTextSplitter(settings.chunk_size, settings.chunk_overlap)
    indexer = Indexer(splitter, store, repository)
    workflow = LangGraphRagWorkflow(store, generator, settings.top_k, settings.relevance_threshold, settings.max_rewrites,
        settings.confidence_high, settings.confidence_medium,
    )
    return Container(
        ingest=IngestDocument(indexer),
        update=UpdateDocument(indexer, repository),
        get_document=GetDocument(repository),
        list_documents=ListDocuments(repository),
        delete=DeleteDocument(repository, store),
        ask=AskQuestion(workflow),
        describe_store=DescribeVectorStore(
            repository,
            store,
            _label(settings.embeddings_provider, settings.embeddings_model),
            _label(settings.llm_provider, settings.llm_model),
        ),
        clear_store=ClearVectorStore(repository, store),
        reindex=ReindexAll(indexer, repository, store),
    )
