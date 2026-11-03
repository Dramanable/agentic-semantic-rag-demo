"""RAG workflow as a LangGraph graph: retrieve -> grade -> (rewrite) -> answer.

The graph only knows the domain ports (VectorStore, TextGenerator).
Each node is timed, logged and measured: this is the traceability of an answer.
Nodes emit domain events (step, sources, token) through LangGraph's stream writer,
so the answer can be streamed to the user while it is being generated.
"""

import logging
from collections.abc import Callable, Iterator
from time import perf_counter
from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph

from app.domain.confidence import assess_confidence
from app.domain.entities import Answer, DoneEvent, ScoredChunk, SourcesEvent, StepEvent, StreamEvent, TokenEvent, TraceStep
from app.domain.ports import TextGenerator, VectorStore
from app.infrastructure.observability import RAG_FIRST_TOKEN, current_request_id, RAG_QUESTIONS, RAG_REWRITES, RAG_STEP_DURATION

NO_ANSWER = "I could not find any relevant information in the documents."

log = logging.getLogger("rag.graph")


class RagState(TypedDict):
    question: str
    query: str
    retrieved: list[ScoredChunk]
    relevant: list[ScoredChunk]
    rewrites: int
    answer: str
    grounded: bool
    steps: list[TraceStep]


NodeResult = tuple[dict[str, Any], str]  # (state update, readable detail)
Emit = Callable[[StreamEvent], None]


class LangGraphRagWorkflow:
    def __init__(
        self,
        store: VectorStore,
        generator: TextGenerator,
        top_k: int,
        relevance_threshold: float,
        max_rewrites: int,
        confidence_high: float = 0.6,
        confidence_medium: float = 0.45,
    ) -> None:
        self._store = store
        self._generator = generator
        self._top_k = top_k
        self._threshold = relevance_threshold
        self._max_rewrites = max_rewrites
        self._confidence_high = confidence_high
        self._confidence_medium = confidence_medium
        self._graph = self._build()

    def stream(self, question: str) -> Iterator[StreamEvent]:
        """Yields steps and sources as they happen, then the answer token by token, then the final answer."""
        initial: RagState = {
            "question": question,
            "query": question,
            "retrieved": [],
            "relevant": [],
            "rewrites": 0,
            "answer": "",
            "grounded": False,
            "steps": [],
        }
        final: RagState = initial
        # Picked up by LangSmith when tracing is enabled: the trace of an answer is found by its request ID.
        config = {"run_name": "semantic_rag", "tags": ["semantic-rag-demo"], "metadata": {"request_id": current_request_id()}}
        for mode, payload in self._graph.stream(initial, config=config, stream_mode=["custom", "values"]):
            if mode == "custom":
                yield payload
            else:
                final = payload
        RAG_QUESTIONS.labels(grounded=str(final["grounded"]).lower()).inc()
        log.info("question answered", extra={"event": "rag.answered", "grounded": final["grounded"], "kept": len(final["relevant"])})
        yield DoneEvent(
            Answer(
                question=question,
                text=final["answer"],
                sources=final["relevant"],
                steps=final["steps"],
                grounded=final["grounded"],
                confidence=assess_confidence(final["relevant"], self._confidence_high, self._confidence_medium),
            )
        )

    def run(self, question: str) -> Answer:
        """Non-streaming convenience: consume the stream and return the final answer."""
        for event in self.stream(question):
            if isinstance(event, DoneEvent):
                return event.answer
        raise RuntimeError("the graph ended without an answer")

    # --- nodes: each returns (update, detail) ------------------------
    def _retrieve(self, state: RagState, emit: Emit) -> NodeResult:
        found = self._store.search(state["query"], self._top_k)
        best = f", best score {found[0].score:.2f}" if found else ""
        return {"retrieved": found}, f"\"{state['query']}\" -> {len(found)} passage(s){best}"

    def _grade(self, state: RagState, emit: Emit) -> NodeResult:
        kept = [s for s in state["retrieved"] if s.score >= self._threshold]
        if kept:
            emit(SourcesEvent(kept))  # the user sees the sources before the answer starts
        return {"relevant": kept}, f"{len(kept)}/{len(state['retrieved'])} passage(s) above threshold {self._threshold}"

    def _rewrite(self, state: RagState, emit: Emit) -> NodeResult:
        rewritten = self._generator.rewrite(state["question"])
        RAG_REWRITES.inc()
        # an identical rewrite would change nothing: stop
        used = state["rewrites"] + 1 if rewritten != state["query"] else self._max_rewrites
        return {"query": rewritten, "rewrites": used}, f'"{rewritten}"'

    def _generate(self, state: RagState, emit: Emit) -> NodeResult:
        started = perf_counter()
        first_token_ms: float | None = None
        pieces: list[str] = []
        for token in self._generator.stream_answer(state["question"], [s.chunk.text for s in state["relevant"]]):
            if first_token_ms is None:
                first_token_ms = round((perf_counter() - started) * 1000, 1)
                RAG_FIRST_TOKEN.observe(first_token_ms / 1000)
            pieces.append(token)
            emit(TokenEvent(token))
        first = f", first token after {first_token_ms} ms" if first_token_ms is not None else ""
        return {"answer": "".join(pieces).strip(), "grounded": True}, f"answer streamed from {len(state['relevant'])} source(s){first}"

    def _give_up(self, state: RagState, emit: Emit) -> NodeResult:
        return {"answer": NO_ANSWER, "grounded": False}, "no relevant source: no invented answer"

    # --- instrumentation ---------------------------------------------------
    def _traced(self, name: str, node: Callable[[RagState, Emit], NodeResult]) -> Callable[[RagState], dict[str, Any]]:
        def run(state: RagState) -> dict[str, Any]:
            emit = get_stream_writer()
            started = perf_counter()
            update, detail = node(state, emit)
            elapsed = perf_counter() - started
            RAG_STEP_DURATION.labels(step=name).observe(elapsed)
            ms = round(elapsed * 1000, 1)
            log.info(detail, extra={"event": "rag.step", "step": name, "duration_ms": ms})
            step = TraceStep(name, detail, ms)
            emit(StepEvent(step))
            return {**update, "steps": [*state["steps"], step]}

        return run

    # --- routing ----------------------------------------------------------
    def _route(self, state: RagState) -> str:
        if state["relevant"]:
            return "generate"
        if state["rewrites"] < self._max_rewrites:
            return "rewrite"
        return "give_up"

    def _build(self):
        graph = StateGraph(RagState)
        for name, node in {
            "retrieve": self._retrieve,
            "grade": self._grade,
            "rewrite": self._rewrite,
            "generate": self._generate,
            "give_up": self._give_up,
        }.items():
            graph.add_node(name, self._traced(name, node))
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges("grade", self._route, ["generate", "rewrite", "give_up"])
        graph.add_edge("rewrite", "retrieve")
        graph.add_edge("generate", END)
        graph.add_edge("give_up", END)
        return graph.compile()
