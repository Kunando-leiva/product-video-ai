"""Excepciones tipadas de la aplicación.

Cada excepción lleva:
- status_code HTTP
- código corto
- mensaje legible
- causa (opcional)
- solución (opcional)

El handler global (app.core.handlers) las convierte en ErrorResponse.
"""
from typing import Optional


class AppError(Exception):
    """Base de todos los errores de dominio."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "Ocurrió un error inesperado."
    cause: Optional[str] = None
    solution: Optional[str] = None

    def __init__(
        self,
        message: Optional[str] = None,
        cause: Optional[str] = None,
        solution: Optional[str] = None,
    ) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        if cause:
            self.cause = cause
        if solution:
            self.solution = solution


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "El recurso solicitado no existe."
    solution = "Verificá el identificador o volvé al listado."


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    message = "Los datos enviados no son válidos."
    solution = "Revisá los campos del formulario."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Ya existe un recurso con esos datos."


class NotReadyError(AppError):
    """Funcionalidad aún no disponible (usado por stubs de routers)."""
    status_code = 501
    code = "not_implemented"
    message = "Esta funcionalidad estará disponible en un módulo posterior."
    solution = "Esperá la próxima versión del backend."


class SecurityError(AppError):
    status_code = 400
    code = "security_error"
    message = "La operación fue rechazada por seguridad."
    solution = "Verificá la ruta o el nombre del archivo."