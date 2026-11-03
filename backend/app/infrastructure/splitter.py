from langchain_text_splitters import Language, RecursiveCharacterTextSplitter


class LangChainTextSplitter:
    """Adapter of the TextSplitter port."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        # Markdown-aware: a heading stays with the paragraph it introduces; plain text falls back to paragraphs/lines/words.
        self._splitter = RecursiveCharacterTextSplitter.from_language(
            Language.MARKDOWN, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def split(self, text: str) -> list[str]:
        return self._splitter.split_text(text)
