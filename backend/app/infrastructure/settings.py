from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """A provider is chosen by name; model, key and URL are generic."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM: extractive | openai | anthropic | mistral | ollama | openai_compatible
    llm_provider: str = "extractive"
    llm_model: str = ""  # empty: the provider's default model
    llm_api_key: str = ""
    llm_base_url: str = ""  # for ollama / openai_compatible (Groq, vLLM, LM Studio, Together…)

    # Embeddings: fastembed | openai | mistral | ollama | openai_compatible
    embeddings_provider: str = "fastembed"
    embeddings_model: str = ""
    embeddings_api_key: str = ""
    embeddings_base_url: str = ""

    # Vector store: chroma | memory
    vector_store_provider: str = "chroma"
    chroma_path: str = "./data/chroma"
    collection: str = "documents"

    documents_path: str = "./data/documents"
    # Kept short on purpose: the default local embeddings model only reads ~128 tokens (~500 characters),
    # anything beyond is silently ignored and would never be searchable.
    chunk_size: int = 400
    chunk_overlap: int = 50
    top_k: int = 4
    relevance_threshold: float = 0.3
    max_rewrites: int = 1
