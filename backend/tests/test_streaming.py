import json

from fastapi.testclient import TestClient

from app.domain.entities import Chunk, DoneEvent, SourcesEvent, StepEvent, TokenEvent
from app.infrastructure.providers.llm import llm_providers
from app.infrastructure.rag_graph import LangGraphRagWorkflow
from app.infrastructure.settings import Settings
from app.infrastructure.text_generators import LangChainTextGenerator
from app.main import create_app
from tests.fakes import FakeGenerator, InMemoryVectorStore
from tests.wiring import build_test_container


def workflow(*texts: str, generator=None) -> LangGraphRagWorkflow:
    store = InMemoryVectorStore()
    store.add_chunks([Chunk(f"d:{i}", "d", t, "d.txt") for i, t in enumerate(texts)])
    return LangGraphRagWorkflow(store, generator or FakeGenerator(), top_k=3, relevance_threshold=0.5, max_rewrites=1)


def parse_sse(body: str) -> list[tuple[str, object]]:
    events = []
    for frame in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_events_come_in_the_promised_order_and_tokens_rebuild_the_answer():
    events = list(workflow("the cat sleeps on the sofa").stream("the cat sleeps"))
    assert [type(e) for e in events] == [
        StepEvent,  # retrieve
        SourcesEvent,  # emitted by grade, before its own step is reported
        StepEvent,  # grade
        TokenEvent,
        TokenEvent,
        StepEvent,  # generate
        DoneEvent,
    ]
    tokens = "".join(e.text for e in events if isinstance(e, TokenEvent))
    done = events[-1].answer
    assert tokens == done.text == "answer(1)"
    assert [s.name for s in done.steps] == ["retrieve", "grade", "generate"]


def test_sources_are_sent_before_the_first_token():
    kinds = [type(e) for e in workflow("the cat sleeps").stream("cat sleeps")]
    assert kinds.index(SourcesEvent) < kinds.index(TokenEvent)


def test_nothing_relevant_streams_no_tokens_and_no_sources():
    events = list(workflow("the cat sleeps", generator=FakeGenerator(rewrite_to="unrelated words")).stream("capital of Japan"))
    assert not any(isinstance(e, (TokenEvent, SourcesEvent)) for e in events)
    assert isinstance(events[-1], DoneEvent) and not events[-1].answer.grounded


def test_first_token_latency_is_part_of_the_generate_step():
    done = list(workflow("the cat sleeps").stream("cat sleeps"))[-1].answer
    assert "first token after" in done.steps[-1].detail


def test_langchain_generator_streams_pieces_not_one_block():
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    pieces = list(LangChainTextGenerator(FakeListChatModel(responses=["hello"])).stream_answer("q", ["p"]))
    assert len(pieces) > 1 and "".join(pieces) == "hello"


def test_extractive_generator_streams_word_by_word_and_loses_nothing():
    gen = llm_providers.build("extractive", Settings())
    pieces = list(gen.stream_answer("q", ["the cat sleeps", "it rains"]))
    assert len(pieces) > 4
    assert "".join(pieces) == "Closest passages:\n\n• the cat sleeps\n\n• it rains"


# --- HTTP: Server-Sent Events -------------------------------------------------
def test_sse_endpoint_streams_typed_events_and_ends_with_done():
    container, *_ = build_test_container()
    with TestClient(create_app(container)) as c:
        c.post("/api/documents/text", json={"source": "n.txt", "text": "the cat sleeps"})
        r = c.post("/api/ask/stream", json={"question": "cat sleeps"}, headers={"X-Request-ID": "abc123"})
        assert r.headers["content-type"].startswith("text/event-stream")
        assert r.headers["cache-control"] == "no-cache" and r.headers["x-accel-buffering"] == "no"
        events = parse_sse(r.text)
        names = [n for n, _ in events]
        assert names[-1] == "done" and "sources" in names and names.index("sources") < names.index("token")
        done = events[-1][1]
        assert done["request_id"] == "abc123" and done["grounded"] and done["answer"] == "answer(1)"
        assert done["confidence"] == {"score": 1.0, "level": "high"}
        assert "".join(d["text"] for n, d in events if n == "token").strip() == done["answer"]


def test_sse_blank_question_is_a_regular_422_before_any_stream_opens():
    container, *_ = build_test_container()
    with TestClient(create_app(container)) as c:
        r = c.post("/api/ask/stream", json={"question": "  "})
        assert r.status_code == 422 and r.json() == {"error": "empty_question"}


class ExplodingGenerator(FakeGenerator):
    def stream_answer(self, question, passages):
        yield "partial"
        raise RuntimeError("secret internal detail")


def test_sse_failure_midway_becomes_an_error_event_without_leaking_details():
    container, *_ = build_test_container(ExplodingGenerator())
    with TestClient(create_app(container)) as c:
        c.post("/api/documents/text", json={"source": "n.txt", "text": "the cat sleeps"})
        r = c.post("/api/ask/stream", json={"question": "cat sleeps"})
        events = parse_sse(r.text)
        assert events[-1] == ("error", {"error": "internal_error"})
        assert "secret internal detail" not in r.text
