from collections.abc import Iterator
from typing import Protocol

from app.domain.entities import StreamEvent


class RagWorkflow(Protocol):
    """Question -> sourced answer orchestration (implemented with LangGraph), as a stream of events."""

    def stream(self, question: str) -> Iterator[StreamEvent]: ...
