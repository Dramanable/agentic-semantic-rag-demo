from app.domain.entities import Document
from app.infrastructure.json_document_repository import JsonDocumentRepository


def test_save_get_list_delete_roundtrip_with_accents(tmp_path):
    repo = JsonDocumentRepository(str(tmp_path))
    doc = Document("rapport-ab12", "Café report.md", "Accented text — é à ç", 3)
    repo.save(doc)
    assert repo.get("rapport-ab12") == doc and repo.list() == [doc]
    assert repo.delete("rapport-ab12") is True and repo.delete("rapport-ab12") is False
    assert repo.get("rapport-ab12") is None


def test_save_overwrites_and_survives_a_new_instance(tmp_path):
    JsonDocumentRepository(str(tmp_path)).save(Document("a", "a", "v1", 1))
    JsonDocumentRepository(str(tmp_path)).save(Document("a", "a", "v2", 1))
    assert JsonDocumentRepository(str(tmp_path)).get("a").text == "v2"


def test_an_identifier_can_never_escape_the_directory(tmp_path):
    repo = JsonDocumentRepository(str(tmp_path / "docs"))
    (tmp_path / "secret.json").write_text("{}")
    assert repo.get("../secret") is None and repo.delete("../secret") is False
