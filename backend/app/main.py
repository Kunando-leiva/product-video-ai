"""Punto de entrada FastAPI."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.db.migrations import apply_migrations
from app.core import ffmpeg
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.handlers import register_exception_handlers
from app.db.init_db import init_db
from app.db.session import engine
from app.audio import tts_router
from app.api import (
    health, projects, media, settings_api,
    engine as engine_api,
    timeline as timeline_api,
    render as render_api,
    subtitles as subtitles_api,
    voice as voice_api,
    music as music_api,
    ai as ai_api,
)
from app.subtitles import stt as stt_mod



configure_logging()
log = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("=== %s v%s iniciando ===", settings.APP_NAME, settings.APP_VERSION)
    log.info("Proyectos:  %s", settings.PROJECTS_DIR)
    log.info("Exports:    %s", settings.EXPORTS_DIR)
    log.info("Logs:       %s", settings.LOGS_DIR)

    if ffmpeg.is_available():
        log.info("FFmpeg disponible: %s", ffmpeg.ffmpeg_path())
        log.info("FFprobe disponible: %s", ffmpeg.ffprobe_path())
    else:
        log.warning(
            "FFmpeg NO disponible. El análisis multimedia funcionará en modo degradado. "
            "Instalalo para habilitar metadata y thumbnails."
        )

    if stt_mod.is_available():
        log.info("Motor de subtítulos (faster-whisper) disponible.")
    else:
        log.warning(
            "faster-whisper NO instalado. La transcripción estará deshabilitada. "
            "Instalalo con: pip install faster-whisper"
        )

    tts = tts_router.get_provider()
    if tts.is_available():
        log.info("Motor de voz (%s) disponible.", tts.name)
    else:
        log.warning(
            "Motor de voz NO disponible. Instalá piper-tts y descargá una voz."
        )

          # ⬇️ NUEVO — Módulo 13
    from app.ai.registry import statuses as ai_statuses
    ai_list = ai_statuses()
    log.info(
        "AI providers: %s",
        ", ".join(f"{s.name}({'✓' if s.available else '✗'})" for s in ai_list),
    )

    await init_db()

    await apply_migrations(engine)

    
    yield
    log.info("=== %s detenido ===", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.mount(
    "/files",
    StaticFiles(directory=str(settings.BASE_DIR)),
    name="files",
)

app.include_router(health.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(timeline_api.router, prefix="/api")
app.include_router(engine_api.router, prefix="/api")
app.include_router(render_api.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(subtitles_api.router, prefix="/api")
app.include_router(voice_api.router, prefix="/api")
app.include_router(music_api.router, prefix="/api")
app.include_router(ai_api.router, prefix="/api")

@app.get("/")
async def root() -> dict:
    return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}