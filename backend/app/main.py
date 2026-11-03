from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError
from app.infrastructure.container import Container, build_container
from app.infrastructure.settings import Settings
from app.infrastructure.observability import configure_logging
from app.presentation.api import domain_error_status, router
from app.presentation.observability import install_observability


def create_app(container: Container | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging()
        app.state.container = container or build_container(Settings())
        yield

    app = FastAPI(title="Semantic RAG demo", lifespan=lifespan)
    app.include_router(router)
    install_observability(app)

    @app.exception_handler(DomainError)
    async def on_domain_error(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(status_code=domain_error_status(error), content={"error": error.code})

    return app


app = create_app()
