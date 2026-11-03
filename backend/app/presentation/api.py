import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.domain.entities import Answer, Document, DoneEvent, SourcesEvent, StepEvent, StreamEvent, TokenEvent
from app.domain.errors import DocumentNotFoundError, DomainError, EmptyDocumentError, EmptyQuestionError
from app.infrastructure.container import Container
from app.infrastructure.observability import current_request_id

MAX_UPLOAD_BYTES = 1_000_000

router = APIRouter(prefix="/api")
log = logging.getLogger("http.stream")

# The HTTP status is a presentation concern: the domain only carries a stable code.
ERROR_STATUS: dict[type[DomainError], int] = {
    EmptyQuestionError: 422,
    EmptyDocumentError: 422,
    DocumentNotFoundError: 404,
}


def domain_error_status(error: DomainError) -> int:
    return ERROR_STATUS.get(type(error), 400)


def get_container(request: Request) -> Container:
    return request.app.state.container


class AskBody(BaseModel):
    question: str = Field(max_length=1000)


class TextBody(BaseModel):
    source: str = Field(min_length=1, max_length=200)
    text: str


class UpdateBody(BaseModel):
    text: str
    source: str | None = Field(default=None, min_length=1, max_length=200)


class SourceOut(BaseModel):
    source: str
    text: str
    score: float


class StepOut(BaseModel):
    name: str
    detail: str
    duration_ms: float


class AnswerOut(BaseModel):
    request_id: str
    question: str
    answer: str
    grounded: bool
    sources: list[SourceOut]
    steps: list[StepOut]


class DocumentOut(BaseModel):
    id: str
    source: str
    chunks: int
    characters: int


class DocumentDetailOut(DocumentOut):
    text: str


class VectorStoreOut(BaseModel):
    provider: str
    embeddings: str
    llm: str
    documents: int
    chunks: int


class ReindexOut(BaseModel):
    documents: int
    chunks: int


def _answer_out(answer: Answer, request_id: str) -> AnswerOut:
    return AnswerOut(
        request_id=request_id,
        question=answer.question,
        answer=answer.text,
        grounded=answer.grounded,
        steps=[StepOut(name=t.name, detail=t.detail, duration_ms=t.duration_ms) for t in answer.steps],
        sources=[SourceOut(source=s.chunk.source, text=s.chunk.text, score=round(s.score, 3)) for s in answer.sources],
    )


def _document_out(d: Document) -> DocumentOut:
    return DocumentOut(id=d.id, source=d.source, chunks=d.chunk_count, characters=len(d.text))


def _detail_out(d: Document) -> DocumentDetailOut:
    return DocumentDetailOut(**_document_out(d).model_dump(), text=d.text)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ask", response_model=AnswerOut)
def ask(body: AskBody, c: Container = Depends(get_container)) -> AnswerOut:
    return _answer_out(c.ask(body.question), current_request_id())


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_frame(event: StreamEvent, request_id: str) -> str:
    match event:
        case StepEvent(step):
            return _sse("step", StepOut(name=step.name, detail=step.detail, duration_ms=step.duration_ms).model_dump())
        case SourcesEvent(sources):
            return _sse("sources", [SourceOut(source=s.chunk.source, text=s.chunk.text, score=round(s.score, 3)).model_dump() for s in sources])
        case TokenEvent(text):
            return _sse("token", {"text": text})
        case DoneEvent(answer):
            return _sse("done", _answer_out(answer, request_id).model_dump())


def _sse_stream(events: Iterator[StreamEvent], request_id: str) -> Iterator[str]:
    try:
        for event in events:
            yield _sse_frame(event, request_id)
    except DomainError as error:
        yield _sse("error", {"error": error.code})
    except Exception:  # never leak internals to the client; the log has the stack trace and the request id
        log.exception("stream failed", extra={"event": "http.stream_failed"})
        yield _sse("error", {"error": "internal_error"})


@router.post("/ask/stream")
def ask_stream(body: AskBody, c: Container = Depends(get_container)) -> StreamingResponse:
    """Server-Sent Events: step, sources, token (many), done. Errors after the start arrive as an `error` event."""
    events = c.ask.stream(body.question)  # validates before the stream opens: a blank question is a normal 422
    return StreamingResponse(
        _sse_stream(events, current_request_id()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # no proxy buffering
    )


# --- documents: add, read, edit, delete -------------------------
@router.get("/documents", response_model=list[DocumentOut])
def documents(c: Container = Depends(get_container)) -> list[DocumentOut]:
    return [_document_out(d) for d in c.list_documents()]


@router.get("/documents/{document_id}", response_model=DocumentDetailOut)
def document(document_id: str, c: Container = Depends(get_container)) -> DocumentDetailOut:
    return _detail_out(c.get_document(document_id))


@router.post("/documents/text", response_model=DocumentOut, status_code=201)
def add_text(body: TextBody, c: Container = Depends(get_container)) -> DocumentOut:
    return _document_out(c.ingest(body.source, body.text))


@router.post("/documents/upload", response_model=DocumentOut, status_code=201)
async def upload(file: UploadFile = File(...), c: Container = Depends(get_container)) -> DocumentOut:
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file_too_large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="text_files_only") from None
    return _document_out(c.ingest(file.filename or "document", text))


@router.put("/documents/{document_id}", response_model=DocumentOut)
def update(document_id: str, body: UpdateBody, c: Container = Depends(get_container)) -> DocumentOut:
    return _document_out(c.update(document_id, body.text, body.source))


@router.delete("/documents/{document_id}", status_code=204)
def delete(document_id: str, c: Container = Depends(get_container)) -> None:
    c.delete(document_id)


# --- vector store: status, clearing, reindexing --------------------------
@router.get("/vector-store", response_model=VectorStoreOut)
def vector_store(c: Container = Depends(get_container)) -> VectorStoreOut:
    info = c.describe_store()
    return VectorStoreOut(
        provider=info.provider, embeddings=info.embeddings, llm=info.llm, documents=info.documents, chunks=info.chunks
    )


@router.delete("/vector-store", status_code=204)
def clear_vector_store(c: Container = Depends(get_container)) -> None:
    c.clear_store()


@router.post("/vector-store/reindex", response_model=ReindexOut)
def reindex(c: Container = Depends(get_container)) -> ReindexOut:
    documents_count, chunks = c.reindex()
    return ReindexOut(documents=documents_count, chunks=chunks)
