from app.application.evaluation import EvalCase, evaluate
from app.domain.entities import NO_CONFIDENCE, Answer, Chunk, Confidence, ScoredChunk


def answer(sources: list[str], level="high", score=0.8) -> Answer:
    scored = [ScoredChunk(Chunk(f"{s}:0", s, "t", s), score) for s in sources]
    return Answer("q", "a", scored, grounded=bool(sources), confidence=Confidence(score, level) if sources else NO_CONFIDENCE)


def run(cases: list[EvalCase], responses: dict[str, Answer]):
    return evaluate(lambda q: responses[q], cases)


def test_perfect_system():
    report = run(
        [EvalCase("a?", "a.md"), EvalCase("zzz?", None)],
        {"a?": answer(["a.md"]), "zzz?": answer([])},
    )
    assert (report.hit_rate, report.mrr, report.abstention_rate, report.accuracy) == (1.0, 1.0, 1.0, 1.0)


def test_rank_and_mrr_use_distinct_sources_best_first():
    report = run([EvalCase("a?", "a.md")], {"a?": answer(["b.md", "b.md", "a.md"])})
    assert report.results[0].rank == 2 and report.mrr == 0.5 and report.hit_rate == 1.0


def test_missing_expected_source_is_a_miss():
    report = run([EvalCase("a?", "a.md")], {"a?": answer(["b.md"])})
    assert report.results[0].rank is None and report.hit_rate == 0.0 and report.mrr == 0.0


def test_answering_an_unanswerable_question_is_a_failure():
    report = run([EvalCase("zzz?", None)], {"zzz?": answer(["a.md"])})
    assert report.abstention_rate == 0.0 and not report.results[0].correct


def test_abstaining_on_an_answerable_question_is_a_failure():
    report = run([EvalCase("a?", "a.md")], {"a?": answer([])})
    assert report.hit_rate == 0.0 and report.accuracy == 0.0


def test_confidence_gap_and_accuracy_by_level():
    report = run(
        [EvalCase("a?", "a.md"), EvalCase("b?", "b.md"), EvalCase("zzz?", None)],
        {
            "a?": answer(["a.md"], "high", 0.8),
            "b?": answer(["a.md"], "high", 0.7),  # confidently wrong
            "zzz?": answer(["a.md"], "low", 0.35),  # answered although it should not
        },
    )
    assert report.accuracy_by_level == {"high": (1, 2), "low": (0, 1)}
    assert round(report.mean_confidence_answerable, 2) == 0.75
    assert round(report.confidence_gap, 2) == 0.40


def test_empty_dataset_does_not_divide_by_zero():
    report = evaluate(lambda q: answer([]), [])
    assert report.accuracy == 0.0 and report.mean_latency_ms == 0.0
