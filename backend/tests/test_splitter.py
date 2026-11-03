from app.infrastructure.splitter import LangChainTextSplitter

LAW = "# The Law\n\nIntro text.\n\n## Article 1 - Scope\n\nFirst paragraph about cats.\n\n## Article 2 - Duties\n\nSecond paragraph about dogs."


def split(text: str, size: int = 400, overlap: int = 0) -> list[str]:
    return LangChainTextSplitter(chunk_size=size, chunk_overlap=overlap).split(text)


def test_every_passage_carries_its_heading_path():
    pieces = split(LAW)
    assert "The Law > Article 1 - Scope\nFirst paragraph about cats." in pieces
    assert "The Law > Article 2 - Duties\nSecond paragraph about dogs." in pieces


def test_a_heading_never_becomes_a_passage_on_its_own():
    assert all("\n" in p for p in split(LAW))


def test_a_long_article_keeps_its_title_on_every_continuation():
    body = " ".join(f"word{i}" for i in range(200))
    pieces = split(f"# Law\n\n## Article 9 - Long\n\n{body}", size=120)
    assert len(pieces) > 3
    assert all(p.startswith("Law > Article 9 - Long\n") for p in pieces)


def test_the_same_article_number_in_two_laws_stays_distinguishable():
    pieces = split("# Law A\n\n## Article 5\n\ntext a\n\n# Law B\n\n## Article 5\n\ntext b")
    assert [p.split("\n")[0] for p in pieces] == ["Law A > Article 5", "Law B > Article 5"]


def test_the_body_of_a_passage_never_exceeds_the_chunk_size():
    long_text = " ".join(f"word{i}" for i in range(400))
    assert all(len(p) <= 300 for p in split(long_text, size=300, overlap=40))


def test_plain_text_without_headings_is_split_without_a_prefix():
    pieces = split("one two three four five six seven eight nine ten", size=30)
    assert len(pieces) > 1 and all(not p.startswith(" ") and "\n" not in p for p in pieces)


def test_blank_text_gives_no_passage():
    assert split("  \n\n ") == []
