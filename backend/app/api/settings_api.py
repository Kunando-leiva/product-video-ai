"""Endpoints de configuración (IA, modelos, voz, etc.).

Módulo 3: stubs. Se implementan en módulos posteriores.
"""
from fastapi import APIRouter

from app.core.errors import NotReadyError


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings() -> None:
    raise NotReadyError(
        message="Leer configuración estará disponible en el Módulo 16.",
    )


@router.put("")
async def update_settings() -> None:
    raise NotReadyError(
        message="Guardar configuración estará disponible en el Módulo 16.",
    )