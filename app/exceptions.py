from __future__ import annotations

from collections.abc import Mapping
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_body(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "Request validation failed."),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        messages: Mapping[int, tuple[str, str]] = {
            401: ("UNAUTHORIZED", "Missing or invalid bearer token."),
            404: ("NOT_FOUND", str(exc.detail)),
            405: ("METHOD_NOT_ALLOWED", "The requested method is not allowed."),
        }
        code, message = messages.get(
            exc.status_code, ("HTTP_ERROR", str(exc.detail) if isinstance(exc.detail, str) else "Request failed.")
        )
        return JSONResponse(status_code=exc.status_code, content=error_body(code, message))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        logger.error("Unexpected request failure.")
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_SERVER_ERROR", "An unexpected server error occurred."),
        )
