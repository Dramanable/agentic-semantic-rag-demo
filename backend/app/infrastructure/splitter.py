from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


class LangChainTextSplitter:
    """Adapter of the TextSplitter port: contextual chunks.

    The text is cut along its Markdown headings, then each section into passages of at most `chunk_size`
    characters. Every passage is prefixed with its heading path ("Law > Article 17 - Right to erasure"),
    so a passage keeps its context when it is retrieved alone: "Article 5" exists in several laws, and a
    continuation of a long article would otherwise lose its title. Plain text without headings is split
    by paragraphs, lines and words.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._sections = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS, strip_headers=True)
        self._body = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def split(self, text: str) -> list[str]:
        pieces: list[str] = []
        for section in self._sections.split_text(text):
            path = " > ".join(section.metadata[key] for _, key in HEADERS if key in section.metadata)
            for part in self._body.split_text(section.page_content):
                pieces.append(f"{path}\n{part}" if path else part)
        return pieces
