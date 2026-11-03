from app.domain.entities import NO_CONFIDENCE, Confidence, ScoredChunk


def assess_confidence(sources: list[ScoredChunk], high: float, medium: float) -> Confidence:
    """Confidence of an answer = similarity of its best source, bucketed.

    No source means no answer, hence no confidence. The thresholds depend on the embeddings model:
    calibrate them with `make eval`.
    """
    if not sources:
        return NO_CONFIDENCE
    best = max(s.score for s in sources)
    level = "high" if best >= high else "medium" if best >= medium else "low"
    return Confidence(score=round(best, 3), level=level)
