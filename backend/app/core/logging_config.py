"""Configuración centralizada de logging.

- Escribe a consola y a archivo rotativo en logs/app.log.
- Formato consistente: timestamp | level | logger | mensaje.
- Se invoca una sola vez al importar app.core.logging_config.
"""
import logging
import logging.handlers
from pathlib import Path

from app.core.config import settings


_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configura handlers de consola + archivo rotativo. Idempotente."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(level)

    # Limpiar handlers previos (por si uvicorn o pytest ya agregaron)
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Consola
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Archivo rotativo
    log_file: Path = settings.LOGS_DIR / "app.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Bajar el ruido de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Helper para obtener loggers con nombre jerárquico."""
    return logging.getLogger(name)