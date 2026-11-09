"""Tests de seguridad de rutas (Regla 56)."""
import pytest

from app.core.errors import SecurityError
from app.core.config import settings
from app.core.paths import (
    assert_safe_id,
    is_safe_id,
    project_dir,
    resolve_within,
    sanitize_filename,
)


def test_safe_id_accepts_valid() -> None:
    assert is_safe_id("project_001")
    assert is_safe_id("ABC-123")
    assert is_safe_id("a")


def test_safe_id_rejects_traversal() -> None:
    assert not is_safe_id("../etc/passwd")
    assert not is_safe_id("foo/bar")
    assert not is_safe_id("")
    assert not is_safe_id("a b")


def test_assert_safe_id_raises() -> None:
    with pytest.raises(SecurityError):
        assert_safe_id("../evil")


def test_sanitize_filename_strips_path() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("/tmp/foo.png") == "foo.png"
    assert sanitize_filename("a b c.mp4") == "a b c.mp4"


def test_sanitize_filename_blocks_empty() -> None:
    with pytest.raises(SecurityError):
        sanitize_filename("...")


def test_resolve_within_blocks_traversal() -> None:
    with pytest.raises(SecurityError):
        resolve_within(settings.PROJECTS_DIR, "..", "..", "etc")


def test_project_dir_ok() -> None:
    p = project_dir("project_001")
    assert str(p).startswith(str(settings.PROJECTS_DIR.resolve()))


def test_project_dir_rejects_bad_id() -> None:
    with pytest.raises(SecurityError):
        project_dir("../evil")