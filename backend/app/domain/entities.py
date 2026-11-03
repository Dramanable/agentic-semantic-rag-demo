"""Domain entities: no framework dependency."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Document:
    """A source document: its full text is kept so it can be edited and re-indexed."""

    id: str
    source: str
    text: str
    chunk_count: int = 0


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    text: str
    source: str


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float  # semantic similarity normalised between 0 and 1


@dataclass(frozen=True)
class TraceStep:
    """A reasoning step: what happened, and how long it took."""

    name: str
    detail: str
    duration_ms: float


ConfidenceLevel = Literal["none", "low", "medium", "high"]


@dataclass(frozen=True)
class Confidence:
    """How closely the best source matches the question (retrieval confidence, not a guarantee of truth)."""

    score: float  # 0..1
    level: ConfidenceLevel


NO_CONFIDENCE = Confidence(score=0.0, level="none")


@dataclass
class Answer:
    question: str
    text: str
    sources: list[ScoredChunk] = field(default_factory=list)
    steps: list[TraceStep] = field(default_factory=list)
    grounded: bool = True  # False: no relevant source, no invented answer
    confidence: Confidence = NO_CONFIDENCE


@dataclass(frozen=True)
class StepEvent:
    step: TraceStep


@dataclass(frozen=True)
class SourcesEvent:
    sources: list[ScoredChunk]


@dataclass(frozen=True)
class TokenEvent:
    text: str


@dataclass(frozen=True)
class DoneEvent:
    answer: Answer


# What a streamed answer is made of, in order: steps, then sources, then tokens, then done.
StreamEvent = StepEvent | SourcesEvent | TokenEvent | DoneEvent


def chunk_ids(document: Document) -> list[str]:
    """A document's passages have deterministic ids: they can be removed from any store."""
    return [f"{document.id}:{i}" for i in range(document.chunk_count)]
