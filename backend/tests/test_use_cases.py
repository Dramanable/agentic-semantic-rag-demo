import pytest

from app.application.use_cases import AskQuestion, document_id_for
from app.domain.entities import chunk_ids
from app.domain.errors import DocumentNotFoundError, EmptyDocumentError, EmptyQuestionError
from tests.wiring import build_test_container


def test_ingest_splits_stores_and_remembers_the_full_text():
    c, store, repo = build_test_container()
    doc = c.ingest("a.txt", "un\n\ndeux\ntrois")
    assert doc.chunk_count == 3 and len(store.chunks) == 3
    assert repo.get(doc.id).text == "un\n\ndeux\ntrois"


def test_ingest_same_source_replaces_instead_of_duplicating():
    c, store, _ = build_test_container()
    c.ingest("a.txt", "un\ndeux")
    c.ingest("a.txt", "trois")
    assert [x.text for x in store.chunks.values()] == ["trois"]


@pytest.mark.parametrize("text", ["", "   \n \n"])
def test_ingest_rejects_empty_document(text):
    c, store, repo = build_test_container()
    with pytest.raises(EmptyDocumentError):
        c.ingest("a.txt", text)
    assert not store.chunks and not repo.documents


def test_update_changes_text_and_reindexes_only_that_document():
    c, store, _ = build_test_container()
    a = c.ingest("a.txt", "un\ndeux\ntrois")
    b = c.ingest("b.txt", "quatre")
    updated = c.update(a.id, "cinq")
    assert updated.chunk_count == 1 and updated.id == a.id
    assert sorted(x.text for x in store.chunks.values()) == ["cinq", "quatre"]
    assert b.id in {x.document_id for x in store.chunks.values()}


def test_update_can_rename_the_source_and_keeps_the_id():
    c, store, _ = build_test_container()
    a = c.ingest("a.txt", "un")
    renamed = c.update(a.id, "un", source="nouveau.txt")
    assert renamed.id == a.id and renamed.source == "nouveau.txt"
    assert {x.source for x in store.chunks.values()} == {"nouveau.txt"}


def test_failed_update_leaves_the_previous_version_untouched():
    c, store, repo = build_test_container()
    a = c.ingest("a.txt", "un\ndeux")
    with pytest.raises(EmptyDocumentError):
        c.update(a.id, "  ")
    assert repo.get(a.id).text == "un\ndeux" and len(store.chunks) == 2


def test_update_and_get_and_delete_unknown_document():
    c, *_ = build_test_container()
    for call in (lambda: c.update("nope", "x"), lambda: c.get_document("nope"), lambda: c.delete("nope")):
        with pytest.raises(DocumentNotFoundError):
            call()


def test_delete_removes_text_and_passages():
    c, store, repo = build_test_container()
    a = c.ingest("a.txt", "un\ndeux")
    c.delete(a.id)
    assert not store.chunks and not repo.documents


def test_list_documents_is_sorted_by_name():
    c, *_ = build_test_container()
    c.ingest("b.txt", "x")
    c.ingest("A.txt", "y")
    assert [d.source for d in c.list_documents()] == ["A.txt", "b.txt"]


def test_clear_empties_the_index_but_keeps_documents():
    c, store, repo = build_test_container()
    c.ingest("a.txt", "un\ndeux")
    c.clear_store()
    info = c.describe_store()
    assert not store.chunks and len(repo.documents) == 1
    assert (info.documents, info.chunks) == (1, 0)


def test_reindex_rebuilds_the_index_from_documents():
    c, store, _ = build_test_container()
    c.ingest("a.txt", "un\ndeux")
    c.ingest("b.txt", "trois")
    c.clear_store()
    assert c.reindex() == (2, 3)
    assert len(store.chunks) == 3 and c.describe_store().chunks == 3


def test_reindex_repairs_an_index_that_lost_its_data():
    c, store, _ = build_test_container()
    c.ingest("a.txt", "un\ndeux")
    store.chunks.clear()  # vector store replaced / corrupted
    c.reindex()
    assert len(store.chunks) == 2


def test_chunk_ids_are_deterministic():
    c, *_ = build_test_container()
    doc = c.ingest("a.txt", "un\ndeux")
    assert chunk_ids(doc) == [f"{doc.id}:0", f"{doc.id}:1"]


def test_document_id_is_stable_and_ascii():
    assert document_id_for("Café report.md") == document_id_for("Café report.md")
    assert document_id_for("Café report.md").isascii()
    assert document_id_for("a.txt") != document_id_for("b.txt")


def test_ask_rejects_blank_question():
    class Boom:
        def stream(self, question):  # pragma: no cover
            raise AssertionError("must not be called")

    with pytest.raises(EmptyQuestionError):
        AskQuestion(Boom())("   ")
