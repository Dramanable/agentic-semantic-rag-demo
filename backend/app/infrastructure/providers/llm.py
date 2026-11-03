"""LLM providers. To add one: a function decorated with @llm_providers.register("name")."""

from app.domain.ports import TextGenerator
from app.infrastructure.providers.registry import Registry
from app.infrastructure.settings import Settings
from app.infrastructure.text_generators import ExtractiveTextGenerator, LangChainTextGenerator

llm_providers: Registry[TextGenerator] = Registry("LLM")

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5",
    "mistral": "mistral-small-latest",
    "ollama": "llama3.2",
}
OLLAMA_URL = "http://host.docker.internal:11434/v1"


def _model(settings: Settings, provider: str) -> str:
    return settings.llm_model or DEFAULT_MODELS.get(provider, "")


@llm_providers.register("extractive")
def _extractive(settings: Settings) -> TextGenerator:
    return ExtractiveTextGenerator()


@llm_providers.register("openai")
def _openai(settings: Settings) -> TextGenerator:
    from langchain_openai import ChatOpenAI

    return LangChainTextGenerator(ChatOpenAI(model=_model(settings, "openai"), api_key=settings.llm_api_key, temperature=0))


@llm_providers.register("anthropic")
def _anthropic(settings: Settings) -> TextGenerator:
    from langchain_anthropic import ChatAnthropic

    return LangChainTextGenerator(
        ChatAnthropic(model=_model(settings, "anthropic"), api_key=settings.llm_api_key, temperature=0)
    )


@llm_providers.register("mistral")
def _mistral(settings: Settings) -> TextGenerator:
    from langchain_mistralai import ChatMistralAI

    return LangChainTextGenerator(
        ChatMistralAI(model=_model(settings, "mistral"), api_key=settings.llm_api_key, temperature=0)
    )


@llm_providers.register("openai_compatible")
def _openai_compatible(settings: Settings, default_url: str = "") -> TextGenerator:
    """Any server speaking the OpenAI protocol: Groq, vLLM, LM Studio, Together, Ollama…"""
    from langchain_openai import ChatOpenAI

    return LangChainTextGenerator(
        ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key or "not-needed",
            base_url=settings.llm_base_url or default_url or None,
            temperature=0,
        )
    )


@llm_providers.register("ollama")
def _ollama(settings: Settings) -> TextGenerator:
    from langchain_openai import ChatOpenAI

    return LangChainTextGenerator(
        ChatOpenAI(
            model=_model(settings, "ollama"),
            api_key=settings.llm_api_key or "ollama",
            base_url=settings.llm_base_url or OLLAMA_URL,
            temperature=0,
        )
    )
