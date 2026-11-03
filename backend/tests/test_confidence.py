import pytest

from app.domain.confidence import assess_confidence
from app.domain.entities import Chunk, ScoredChunk


def sources(*scores: float) -> list[ScoredChunk]:
    return [ScoredChunk(Chunk(f"d:{i}", "d", "t", "d.txt"), s) for i, s in enumerate(scores)]


def test_no_source_means_no_confidence():
    result = assess_confidence([], high=0.6, medium=0.45)
    assert (result.score, result.level) == (0.0, "none")


@pytest.mark.parametrize(
    "best,level",
    [(0.9, "high"), (0.6, "high"), (0.59, "medium"), (0.45, "medium"), (0.44, "low"), (0.3, "low")],
)
def test_levels_follow_the_thresholds_on_the_best_source(best, level):
    assert assess_confidence(sources(0.31, best), high=0.6, medium=0.45).level == level


def test_the_score_is_the_best_source_similarity():
    assert assess_confidence(sources(0.4, 0.7234567), high=0.6, medium=0.45).score == 0.723
