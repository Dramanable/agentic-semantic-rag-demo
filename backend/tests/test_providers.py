import pytest

from app.infrastructure.providers.embeddings import embeddings_providers
from app.infrastructure.providers.llm import llm_providers
from app.infrastructure.providers.registry import ConfigurationError, Registry
from app.infrastructure.providers.vector_stores import vector_store_providers
from app.infrastructure.settings import Settings
from app.infrastructure.text_generators import ExtractiveTextGenerator, LangChainTextGenerator


def test_all_documented_providers_are_registered():
    assert {"extractive", "openai", "anthropic", "mistral", "ollama", "openai_compatible"} <= set(llm_providers.names())
    assert {"fastembed", "openai", "mistral", "ollama", "openai_compatible"} <= set(embeddings_providers.names())
    assert {"chroma", "memory"} <= set(vector_store_providers.names())


def test_unknown_provider_fails_with_the_list_of_available_ones():
    with pytest.raises(ConfigurationError, match="Available: .*openai"):
        llm_providers.build("unknown", Settings())


def test_a_new_provider_is_added_without_touching_existing_code():
    registry: Registry[ExtractiveTextGenerator] = Registry("LLM")

    @registry.register("my-llm")
    def build(settings):
        return ExtractiveTextGenerator()

    assert isinstance(registry.build("my-llm", Settings()), ExtractiveTextGenerator)


def test_extractive_needs_no_key_and_never_invents():
    gen = llm_providers.build("extractive", Settings())
    assert "cat" in "".join(gen.stream_answer("q", ["the cat"])) and gen.rewrite("q") == "q"


def test_any_langchain_chat_model_plugs_into_the_port():
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    gen = LangChainTextGenerator(FakeListChatModel(responses=["hello", "rewritten question"]))
    assert "".join(gen.stream_answer("q", ["p"])) == "hello"
    assert gen.rewrite("q") == "rewritten question"


@pytest.mark.parametrize("provider", ["openai", "anthropic", "mistral", "ollama", "openai_compatible"])
def test_remote_llm_providers_build_without_network(provider):
    settings = Settings(llm_provider=provider, llm_api_key="k", llm_model="m", llm_base_url="http://localhost:1/v1")
    assert isinstance(llm_providers.build(provider, settings), LangChainTextGenerator)
