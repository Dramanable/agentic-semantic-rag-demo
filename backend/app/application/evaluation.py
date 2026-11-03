"""Offline evaluation of the RAG: does it find the right source, does it abstain when it should,
and is its confidence meaningful? Pure logic: it only needs a function that answers a question."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from app.domain.entities import Answer, Confidence


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_source: str | None  # None: the documents cannot answer; the right behaviour is to abstain


@dataclass(frozen=True)
class CaseResult:
    case: EvalCase
    grounded: bool
    sources: list[str]  # distinct source names, best first
    rank: int | None  # 1-based rank of the expected source
    correct: bool
    confidence: Confidence
    latency_ms: float


@dataclass(frozen=True)
class EvalReport:
    results: list[CaseResult]
    answerable: int
    unanswerable: int
    hit_rate: float  # answerable questions whose expected source was retrieved
    mrr: float  # mean reciprocal rank of the expected source
    abstention_rate: float  # unanswerable questions correctly left unanswered
    accuracy: float  # overall
    mean_confidence_answerable: float
    mean_confidence_unanswerable: float
    accuracy_by_level: dict[str, tuple[int, int]]  # level -> (correct, total): is confidence trustworthy?
    mean_latency_ms: float

    @property
    def confidence_gap(self) -> float:
        """How well confidence separates answerable from unanswerable questions (higher is better)."""
        return self.mean_confidence_answerable - self.mean_confidence_unanswerable


def _ratio(numerator: float, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _evaluate_case(ask: Callable[[str], Answer], case: EvalCase) -> CaseResult:
    started = perf_counter()
    answer = ask(case.question)
    latency = round((perf_counter() - started) * 1000, 1)
    sources = list(dict.fromkeys(s.chunk.source for s in answer.sources))
    if case.expected_source is None:
        rank, correct = None, not answer.grounded
    else:
        rank = sources.index(case.expected_source) + 1 if case.expected_source in sources else None
        correct = answer.grounded and rank is not None
    return CaseResult(case, answer.grounded, sources, rank, correct, answer.confidence, latency)


def evaluate(ask: Callable[[str], Answer], cases: list[EvalCase]) -> EvalReport:
    results = [_evaluate_case(ask, case) for case in cases]
    answerable = [r for r in results if r.case.expected_source is not None]
    unanswerable = [r for r in results if r.case.expected_source is None]
    by_level: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        by_level[r.confidence.level].append(r.correct)
    return EvalReport(
        results=results,
        answerable=len(answerable),
        unanswerable=len(unanswerable),
        hit_rate=_ratio(sum(r.correct for r in answerable), len(answerable)),
        mrr=_ratio(sum(1 / r.rank for r in answerable if r.rank), len(answerable)),
        abstention_rate=_ratio(sum(r.correct for r in unanswerable), len(unanswerable)),
        accuracy=_ratio(sum(r.correct for r in results), len(results)),
        mean_confidence_answerable=_ratio(sum(r.confidence.score for r in answerable), len(answerable)),
        mean_confidence_unanswerable=_ratio(sum(r.confidence.score for r in unanswerable), len(unanswerable)),
        accuracy_by_level={level: (sum(v), len(v)) for level, v in by_level.items()},
        mean_latency_ms=round(_ratio(sum(r.latency_ms for r in results), len(results)), 1),
    )
