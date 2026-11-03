"""The same tests against every vector store: that is what makes the adapters interchangeable."""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.domain.entities import Chunk
from app.infrastructure.providers.vector_stores import vector_store_providers
from app.infrastructure.settings import Settings


@pytest.fixture(params=["chroma", "memory"])
def store(request, tmp_path):
    settings = Settings(chroma_path=str(tmp_path / "chroma"), collection="test_docs")
    return vector_store_providers.build(request.param, settings, DeterministicFakeEmbedding(size=32))


def chunks():
    return [Chunk(f"d:{i}", "d", t, "d.txt") for i, t in enumerate(["the cat sleeps", "the stock market rises", "it rains"])]


def test_exact_text_is_found_first_with_its_metadata(store):
    store.add_chunks(chunks())
    best = store.search("the stock market rises", k=3)[0]
    assert best.chunk.text == "the stock market rises" and best.chunk.source == "d.txt" and best.chunk.document_id == "d"
    assert 0.99 <= best.score <= 1.0


def test_scores_stay_between_0_and_1(store):
    store.add_chunks(chunks())
    assert all(0.0 <= r.score <= 1.0 for r in store.search("something else", k=3))


def test_deleted_chunks_are_no_longer_found(store):
    store.add_chunks(chunks())
    store.delete_chunks(["d:1"])
    assert "the stock market rises" not in [r.chunk.text for r in store.search("the stock market rises", k=5)]


def test_clear_empties_the_store_and_it_stays_usable(store):
    store.add_chunks(chunks())
    store.clear()
    assert store.search("the cat sleeps", k=3) == []
    store.add_chunks(chunks()[:1])
    assert store.search("the cat sleeps", k=3)[0].chunk.id == "d:0"


def test_empty_operations_are_harmless(store):
    store.add_chunks([])
    store.delete_chunks([])
    assert store.search("rien", k=3) == []
