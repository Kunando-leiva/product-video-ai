"""Modelos Pydantic compartidos por toda la API."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Formato estándar de error de la API.

    Regla 47: nunca exponer 'Error 500' al usuario.
    Siempre: mensaje + causa + solución sugerida.
    """
    error: str = Field(..., description="Código corto del error")
    message: str = Field(..., description="Mensaje legible para el usuario")
    cause: Optional[str] = Field(None, description="Causa técnica")
    solution: Optional[str] = Field(None, description="Cómo resolverlo")
    detail: Optional[Any] = Field(None, description="Detalle adicional opcional")


class MessageResponse(BaseModel):
    """Respuesta genérica con un solo mensaje."""
    message: str