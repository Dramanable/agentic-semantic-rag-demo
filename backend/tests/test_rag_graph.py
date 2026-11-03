from app.domain.entities import Chunk
from app.infrastructure.rag_graph import NO_ANSWER, LangGraphRagWorkflow
from tests.fakes import FakeGenerator, InMemoryVectorStore


def store_with(*texts: str) -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    store.add_chunks([Chunk(f"d:{i}", "d", t, "d.txt") for i, t in enumerate(texts)])
    return store


def workflow(store, generator, max_rewrites=1):
    return LangGraphRagWorkflow(store, generator, top_k=3, relevance_threshold=0.5, max_rewrites=max_rewrites)


def test_relevant_passage_is_answered_with_sources_and_no_rewrite():
    gen = FakeGenerator()
    answer = workflow(store_with("the cat sleeps on the sofa", "the stock market rises"), gen).run("where the cat sleeps")
    assert answer.grounded and answer.text == "answer(1)"
    assert [s.chunk.text for s in answer.sources] == ["the cat sleeps on the sofa"]
    assert gen.rewrite_calls == 0


def test_irrelevant_question_is_rewritten_then_answered():
    gen = FakeGenerator(rewrite_to="cat sofa")
    answer = workflow(store_with("the cat sleeps on the sofa"), gen).run("where does it nap")
    assert answer.grounded
    assert gen.rewrite_calls == 1
    assert any(step.name == "rewrite" for step in answer.steps)


def test_nothing_relevant_gives_up_without_inventing():
    gen = FakeGenerator(rewrite_to="still nothing")
    answer = workflow(store_with("the cat sleeps"), gen).run("capital of Japan")
    assert not answer.grounded and answer.text == NO_ANSWER and answer.sources == []
    assert gen.rewrite_calls == 1  # a single rewrite, no infinite loop


def test_identical_rewrite_stops_immediately():
    gen = FakeGenerator()  # rewrites identically
    answer = workflow(store_with("the cat sleeps"), gen, max_rewrites=5).run("capital of Japan")
    assert not answer.grounded
    assert gen.rewrite_calls == 1


def test_empty_store_gives_up():
    answer = workflow(InMemoryVectorStore(), FakeGenerator(), max_rewrites=0).run("question")
    assert not answer.grounded


def test_every_node_leaves_a_timed_trace_step():
    answer = workflow(store_with("the cat sleeps on the sofa"), FakeGenerator()).run("where the cat sleeps")
    assert [s.name for s in answer.steps] == ["retrieve", "grade", "generate"]
    assert all(s.duration_ms >= 0 and s.detail for s in answer.steps)
