"""Embedding providers. To add one: @embeddings_providers.register("name")."""

from langchain_core.embeddings import Embeddings

from app.infrastructure.providers.registry import Registry
from app.infrastructure.settings import Settings

embeddings_providers: Registry[Embeddings] = Registry("embeddings")

DEFAULT_MODELS = {
    "fastembed": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "openai": "text-embedding-3-small",
    "mistral": "mistral-embed",
    "ollama": "nomic-embed-text",
}
OLLAMA_URL = "http://host.docker.internal:11434/v1"


def _model(settings: Settings, provider: str) -> str:
    return settings.embeddings_model or DEFAULT_MODELS.get(provider, "")


@embeddings_providers.register("fastembed")
def _fastembed(settings: Settings) -> Embeddings:
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

    return FastEmbedEmbeddings(model_name=_model(settings, "fastembed"))


@embeddings_providers.register("openai")
def _openai(settings: Settings) -> Embeddings:
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=_model(settings, "openai"), api_key=settings.embeddings_api_key)


@embeddings_providers.register("mistral")
def _mistral(settings: Settings) -> Embeddings:
    from langchain_mistralai import MistralAIEmbeddings

    return MistralAIEmbeddings(model=_model(settings, "mistral"), api_key=settings.embeddings_api_key)


@embeddings_providers.register("openai_compatible")
def _openai_compatible(settings: Settings, default_url: str = "") -> Embeddings:
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.embeddings_model,
        api_key=settings.embeddings_api_key or "not-needed",
        base_url=settings.embeddings_base_url or default_url or None,
        check_embedding_ctx_length=False,  # non-OpenAI servers do not use tiktoken
    )


@embeddings_providers.register("ollama")
def _ollama(settings: Settings) -> Embeddings:
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=_model(settings, "ollama"),
        api_key=settings.embeddings_api_key or "ollama",
        base_url=settings.embeddings_base_url or OLLAMA_URL,
        check_embedding_ctx_length=False,
    )
