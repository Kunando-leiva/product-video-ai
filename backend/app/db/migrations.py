"""Migraciones ad-hoc para SQLite.

Como SQLite no soporta ALTER TABLE complejo y no usamos Alembic
por simplicidad, hacemos migraciones defensivas al startup.

Cada migración debe ser IDEMPOTENTE.
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine


log = logging.getLogger("app.db.migrations")


async def apply_migrations(engine: AsyncEngine) -> None:
    """Aplica migraciones pendientes."""
    async with engine.begin() as conn:

        def has_column(sync_conn, table: str, column: str) -> bool:
            insp = inspect(sync_conn)
            try:
                cols = [c["name"] for c in insp.get_columns(table)]
            except Exception:
                return False
            return column in cols

        # ── Migración 1 (Módulo 12): projects.voice_track ────────────
        has = await conn.run_sync(
            lambda c: has_column(c, "projects", "voice_track")
        )
        if not has:
            log.info("Migración: agregando projects.voice_track")
            await conn.execute(
                text(
                    "ALTER TABLE projects "
                    "ADD COLUMN voice_track VARCHAR(2000)"
                )
            )
        else:
            log.debug("projects.voice_track ya existe")

        # ── Migración 2 (Módulo 12): projects.voice_volume ───────────
        has = await conn.run_sync(
            lambda c: has_column(c, "projects", "voice_volume")
        )
        if not has:
            log.info("Migración: agregando projects.voice_volume")
            await conn.execute(
                text(
                    "ALTER TABLE projects "
                    "ADD COLUMN voice_volume FLOAT NOT NULL DEFAULT 1.0"
                )
            )
        else:
            log.debug("projects.voice_volume ya existe")