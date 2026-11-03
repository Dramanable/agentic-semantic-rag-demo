import logging
from time import perf_counter

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.infrastructure.observability import (
    HTTP_DURATION,
    HTTP_REQUESTS,
    new_request_id,
    reset_request_id,
    set_request_id,
)

log = logging.getLogger("http")
REQUEST_ID_HEADER = "X-Request-ID"


def install_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def trace_request(request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        # reuse an upstream proxy's id, bounded and free of exotic characters
        request_id = incoming if 0 < len(incoming) <= 64 and incoming.isalnum() else new_request_id()
        token = set_request_id(request_id)
        started = perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            elapsed = perf_counter() - started
            route = request.scope.get("route")
            path = route.path if route else "unmatched"  # route template: avoids a label explosion
            HTTP_REQUESTS.labels(request.method, path, str(status)).inc()
            HTTP_DURATION.labels(request.method, path).observe(elapsed)
            if path != "/metrics":
                level = logging.ERROR if status >= 500 else logging.INFO
                log.log(
                    level,
                    "request",
                    extra={"event": "http.request", "method": request.method, "path": path, "status": status, "duration_ms": round(elapsed * 1000, 1)},
                )
            reset_request_id(token)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
