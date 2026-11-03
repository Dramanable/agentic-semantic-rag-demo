import re
from collections.abc import Iterator

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You answer only from the provided passages. "
            "If the passages do not contain the answer, say so. "
            "Answer in the language of the question, concisely.",
        ),
        ("human", "Passages:\n{passages}\n\nQuestion: {question}"),
    ]
)

REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the question for a semantic search in a "
            "document base: precise keywords, no pronouns. Reply with the question only.",
        ),
        ("human", "{question}"),
    ]
)


class LangChainTextGenerator:
    """Adapter of the TextGenerator port: works with ANY LangChain chat model."""

    def __init__(self, model: BaseChatModel) -> None:
        self._answer = ANSWER_PROMPT | model | StrOutputParser()
        self._rewrite = REWRITE_PROMPT | model | StrOutputParser()

    def stream_answer(self, question: str, passages: list[str]) -> Iterator[str]:
        joined = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(passages))
        yield from self._answer.stream({"question": question, "passages": joined})

    def rewrite(self, question: str) -> str:
        return self._rewrite.invoke({"question": question}).strip() or question


class ExtractiveTextGenerator:
    """No-LLM mode: returns the retrieved passages, invents nothing."""

    def stream_answer(self, question: str, passages: list[str]) -> Iterator[str]:
        text = "Closest passages:\n\n" + "\n\n".join(f"• {p}" for p in passages)
        yield from re.findall(r"\s*\S+", text)  # word by word, like a model would

    def rewrite(self, question: str) -> str:
        return question
