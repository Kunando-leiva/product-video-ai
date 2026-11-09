"""Exception handlers globales.

Convierten cualquier excepción en ErrorResponse consistente.
Nunca se filtra un stack trace al cliente.
"""
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.models.common import ErrorResponse


log = logging.getLogger("app.errors")


def _to_response(
    status_code: int,
    payload: ErrorResponse,
) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        log.warning(
            "AppError %s: %s | cause=%s",
            exc.code,
            exc.message,
            exc.cause,
        )
        return _to_response(
            exc.status_code,
            ErrorResponse(
                error=exc.code,
                message=exc.message,
                cause=exc.cause,
                solution=exc.solution,
                detail=None,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        log.info("Validation error: %s", exc.errors())
        return _to_response(
            422,
            ErrorResponse(
                error="validation_error",
                message="Los datos enviados no son válidos.",
                cause=None,
                solution="Revisá los campos del formulario.",
                detail=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Mapeamos códigos comunes a mensajes amigables
        mapping = {
            404: ("not_found", "El recurso solicitado no existe.", None),
            405: ("method_not_allowed", "Método HTTP no permitido.", None),
            401: ("unauthorized", "No autorizado.", None),
            403: ("forbidden", "Acción no permitida.", None),
        }
        code, msg, sol = mapping.get(
            exc.status_code,
            ("http_error", str(exc.detail), None),
        )
        return _to_response(
            exc.status_code,
            ErrorResponse(
                error=code,
                message=msg,
                cause=None,
                solution=sol,
                detail=None,
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled exception: %s", exc)
        return _to_response(
            500,
            ErrorResponse(
                error="internal_error",
                message="Ocurrió un error inesperado en el servidor.",
                cause=type(exc).__name__,
                solution="Revisá los logs en logs/app.log.",
                detail=None,
            ),
        )