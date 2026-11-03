from app.infrastructure.splitter import LangChainTextSplitter

DOC = "# Title A\n\nFirst paragraph about cats.\n\n# Title B\n\nSecond paragraph about dogs."


def test_a_heading_is_kept_with_the_paragraph_it_introduces():
    pieces = LangChainTextSplitter(chunk_size=45, chunk_overlap=0).split(DOC)
    assert not any(p.strip() in ("# Title A", "# Title B") for p in pieces)


def test_no_passage_exceeds_the_chunk_size():
    long_text = " ".join(f"word{i}" for i in range(400))
    assert all(len(p) <= 300 for p in LangChainTextSplitter(chunk_size=300, chunk_overlap=40).split(long_text))


def test_plain_text_without_markdown_is_still_split():
    assert len(LangChainTextSplitter(chunk_size=30, chunk_overlap=0).split("one two three four five six seven eight nine ten")) > 1
