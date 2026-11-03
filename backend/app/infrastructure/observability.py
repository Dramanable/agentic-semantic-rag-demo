"""Observability: request id, JSON logs, Prometheus metrics."""

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Fields passed via `extra=` that appear as-is in the JSON log line.
_EXTRA_FIELDS = ("event", "step", "duration_ms", "method", "path", "status", "grounded", "kept", "found")


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(value: str) -> contextvars.Token[str]:
    return _request_id.set(value)


def reset_request_id(token: contextvars.Token[str]) -> None:
    _request_id.reset(token)


def current_request_id() -> str:
    return _request_id.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "service": "semantic-rag-api",
            "request_id": current_request_id(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _EXTRA_FIELDS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    logging.getLogger("uvicorn.access").disabled = True  # replaced by our own access line


HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
HTTP_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "path"])
RAG_QUESTIONS = Counter("rag_questions_total", "Questions asked, by whether a source was found", ["grounded"])
RAG_STEP_DURATION = Histogram("rag_step_duration_seconds", "Duration of each graph step", ["step"])
RAG_REWRITES = Counter("rag_rewrites_total", "Query rewrites triggered")
RAG_FIRST_TOKEN = Histogram("rag_first_token_seconds", "Delay before the first streamed token of an answer")
