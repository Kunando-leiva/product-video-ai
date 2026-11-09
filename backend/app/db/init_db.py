"""Inicialización del esquema al startup."""
import logging

from app.db.base import Base
from app.db.session import engine
# Importar los modelos para que Base.metadata los conozca
from app.models import db_models  # noqa: F401


log = logging.getLogger("app.db")


async def init_db() -> None:
    """Crea las tablas si no existen (idempotente)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Esquema SQLite listo (%d tablas)", len(Base.metadata.tables))