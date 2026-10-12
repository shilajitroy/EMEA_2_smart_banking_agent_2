from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from sqlalchemy.engine import Engine
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.database import create_database_engine, create_session_factory, init_db, seed_demo_customer
from app.exceptions import register_exception_handlers
from app.routers.accounts import router as accounts_router
from app.routers.applications import router as applications_router
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router

CHAT_PAGE = Path(__file__).resolve().parent / "static" / "index.html"


class ConfirmationTokenLogRedaction:
    """Remove cancellation tokens from the request scope before server access logging."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        parts = path.split("/")
        redact_path = (
            len(parts) == 5
            and parts[1] == "api"
            and parts[2] == "loan-applications"
            and parts[3] not in {"", "pending", "submit"}
            and parts[4] == "cancel"
        )

        async def send_with_redacted_access_path(message: Message) -> None:
            if (
                redact_path
                and message["type"] == "http.response.body"
                and not message.get("more_body", False)
            ):
                scope["path"] = "/api/loan-applications/[REDACTED]/cancel"
                if "raw_path" in scope:
                    scope["raw_path"] = b"/api/loan-applications/[REDACTED]/cancel"
            await send(message)

        try:
            await self.app(scope, receive, send_with_redacted_access_path)
        finally:
            if redact_path:
                scope["path"] = "/api/loan-applications/[REDACTED]/cancel"
                if "raw_path" in scope:
                    scope["raw_path"] = b"/api/loan-applications/[REDACTED]/cancel"


def create_app(database_url: str | None = None) -> FastAPI:
    engine: Engine = create_database_engine(database_url or settings.database_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if not settings.banking_api_token:
            raise RuntimeError("BANKING_API_TOKEN must be configured before the API starts.")
        init_db(engine)
        with session_factory() as db:
            seed_demo_customer(db)
        yield
        engine.dispose()

    application = FastAPI(
        title="Smart Banking Agent",
        version="2.0.0",
        description=(
            "Mock banking support for training only. Eligibility is indicative; "
            "application submission is not final loan approval."
        ),
        lifespan=lifespan,
    )
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.chat_sessions = {}
    application.add_middleware(ConfirmationTokenLogRedaction)
    application.include_router(health_router)
    application.include_router(accounts_router)
    application.include_router(applications_router)
    application.include_router(chat_router)

    @application.get("/", include_in_schema=False)
    async def browser_chat() -> FileResponse:
        return FileResponse(CHAT_PAGE, media_type="text/html")

    register_exception_handlers(application)
    return application


app = create_app()
