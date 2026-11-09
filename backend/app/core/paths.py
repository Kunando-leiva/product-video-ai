"""Utilidades seguras para manejo de rutas.

Regla 56: evitar path traversal, sanitizar nombres, limitar rutas
a las carpetas permitidas del proyecto.
"""
import re
from pathlib import Path

from app.core.config import settings
from app.core.errors import SecurityError


_SAFE_ID = re.compile(r"^[A-Za-z0-9_\-]+$")


def is_safe_id(value: str) -> bool:
    """Un ID válido: letras, números, guion y guion bajo. Sin separadores."""
    return bool(value) and bool(_SAFE_ID.match(value))


def assert_safe_id(value: str, kind: str = "id") -> None:
    if not is_safe_id(value):
        raise SecurityError(
            message=f"El {kind} contiene caracteres no permitidos.",
            cause=f"valor={value!r}",
            solution="Usá solo letras, números, guion y guion bajo.",
        )


def sanitize_filename(name: str) -> str:
    """Devuelve un nombre de archivo seguro (sin separadores ni '..')."""
    # Quedarse con el basename
    base = Path(name).name
    # Reemplazar caracteres problemáticos
    base = re.sub(r"[^\w\.\- ]", "_", base)
    base = base.strip().strip(".")
    if not base:
        raise SecurityError(
            message="El nombre del archivo no es válido.",
            cause=f"original={name!r}",
            solution="Elegí un nombre de archivo distinto.",
        )
    return base


def resolve_within(root: Path, *parts: str) -> Path:
    """Resuelve root / parts y garantiza que el resultado quede dentro de root.

    Lanza SecurityError si el resultado escapa del root.
    """
    root_resolved = root.resolve()
    candidate = (root_resolved.joinpath(*parts)).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as e:
        raise SecurityError(
            message="La ruta solicitada está fuera del área permitida.",
            cause=str(e),
            solution="No se permiten rutas absolutas ni '..'.",
        )
    return candidate


def project_dir(project_id: str) -> Path:
    """Ruta segura a projects/<project_id>/."""
    assert_safe_id(project_id, "project id")
    return resolve_within(settings.PROJECTS_DIR, project_id)


def export_dir(project_id: str) -> Path:
    """Ruta segura a exports/<project_id>/."""
    assert_safe_id(project_id, "project id")
    return resolve_within(settings.EXPORTS_DIR, project_id)