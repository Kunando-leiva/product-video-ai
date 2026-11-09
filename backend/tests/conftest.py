"""Fixtures compartidas de pytest."""
import tempfile
from pathlib import Path
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import ffmpeg
from app.db.base import Base
from app.db.session import get_session
from app.main import app




# ------------------------------------------------------------------
# Engine + Session factory de test (compartidos por db_session y async_client)
# ------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_engine():
    """Engine async apuntando a un SQLite temporal, por test."""
    tmpdir = Path(tempfile.mkdtemp(prefix="pvai_test_"))
    db_path = tmpdir / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión async, atada al engine de test."""
    Session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


# ------------------------------------------------------------------
# Cliente SYNC (legacy) — para tests que NO usan BackgroundTasks.
# ------------------------------------------------------------------

@pytest.fixture
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ------------------------------------------------------------------
# Cliente ASYNC — para tests con BackgroundTasks / render.
#
# Overridea DOS cosas:
#   1. get_session          → endpoints usan la DB de test
#   2. _get_session_factory → RenderService._run_job usa la DB de test
#
# La factory se pasa EXPLÍCITAMENTE (no se infiere de db_session),
# porque AsyncSession en SQLAlchemy 2.0 NO expone `.async_session`.
# ------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_client(
    test_engine,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    # Import local para evitar ciclos de import al cargar conftest
    from app.api.render import _get_session_factory

    # La MISMA factory que creó db_session, atada al engine de test
    test_session_factory = async_sessionmaker(
        test_engine, expire_on_commit=False
    )

    async def _override_session():
        yield db_session

    def _override_factory():
        return test_session_factory

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[_get_session_factory] = _override_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


# -------------------- Fixtures de archivos reales --------------------

@pytest.fixture(scope="session")
def sample_video(tmp_path_factory) -> Path:
    """Video MP4 de 2s, 320x240, 24fps generado con FFmpeg."""
    if not ffmpeg.is_available():
        pytest.skip("FFmpeg no disponible; se omiten tests de análisis")
    out = tmp_path_factory.mktemp("media") / "sample.mp4"
    ffmpeg.make_test_video(out, seconds=2.0, fps=24, size="320x240")
    return out


@pytest.fixture(scope="session")
def sample_image(tmp_path_factory) -> Path:
    """Imagen PNG sólida 640x480 generada con FFmpeg."""
    if not ffmpeg.is_available():
        pytest.skip("FFmpeg no disponible; se omiten tests de análisis")
    out = tmp_path_factory.mktemp("media") / "sample.png"
    ffmpeg.make_solid_image(out, width=640, height=480, color="blue")
    return out