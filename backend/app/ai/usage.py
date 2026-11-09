"""Registro de uso de IA (Regla 21).

Cada llamada a un provider deja un registro en `ai_usage`
con: proveedor, tarea, estado, tokens y costo estimado.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import AIUsage


log = logging.getLogger("app.ai.usage")


async def record(
    session: AsyncSession,
    provider: str,
    task: str,
    status: str,
    tokens: int = 0,
    cost_estimate: float = 0.0,
    detail: Optional[str] = None,
) -> None:
    """Inserta un registro de uso. No lanza si falla (best effort)."""
    try:
        usage = AIUsage(
            provider=provider,
            task=task,
            status=status,
            tokens=tokens,
            cost_estimate=cost_estimate,
            detail=(detail or "")[:2000],
        )
        session.add(usage)
        await session.commit()
    except Exception:
        log.exception("No se pudo registrar AIUsage")