"""Vector stores. To add one: @vector_store_providers.register("name")."""

from langchain_core.embeddings import Embeddings

from app.domain.ports import VectorStore
from app.infrastructure.langchain_vector_store import LangChainVectorStore
from app.infrastructure.providers.registry import Registry
from app.infrastructure.settings import Settings

vector_store_providers: Registry[VectorStore] = Registry("vector store")


@vector_store_providers.register("chroma")
def _chroma(settings: Settings, embeddings: Embeddings) -> VectorStore:
    from langchain_chroma import Chroma

    return LangChainVectorStore(
        "chroma",
        lambda: Chroma(
            collection_name=settings.collection,
            embedding_function=embeddings,
            persist_directory=settings.chroma_path,
            collection_metadata={"hnsw:space": "cosine"},
        ),
    )


@vector_store_providers.register("memory")
def _memory(settings: Settings, embeddings: Embeddings) -> VectorStore:
    from langchain_core.vectorstores import InMemoryVectorStore

    return LangChainVectorStore("memory", lambda: InMemoryVectorStore(embeddings))
