"""Lógica de negocio de voz."""
import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.audio import tts_router
from app.audio.tts_local import LocalPiperTTS
from app.audio.voices import list_voices
from app.core.config import settings
from app.core.errors import ValidationError
from app.core.paths import project_dir
from app.models.voice import (
    SynthesizeRequest,
    SynthesizeResponse,
    VoiceInfo,
    VoiceListResponse,
)
from app.services.project_service import ProjectService


log = logging.getLogger("app.services.voice")


class VoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)

    async def list_voices(self) -> VoiceListResponse:
        voices = list_voices()
        provider = tts_router.get_provider()
        return VoiceListResponse(
            available=provider.is_available(),
            provider=provider.name,
            voices=[
                VoiceInfo(
                    id=v.id,
                    name=v.name,
                    language=v.language,
                    quality=v.quality,
                    gender=v.gender,
                )
                for v in voices
            ],
        )

    async def synthesize(
        self, project_id: str, req: SynthesizeRequest
    ) -> SynthesizeResponse:
        await self.projects.get_project(project_id)

        if not req.text.strip():
            raise ValidationError(
                message="El texto está vacío.",
                solution="Escribí algo para narrar.",
            )

        provider = tts_router.get_provider()
        if not provider.is_available():
            raise ValidationError(
                message="El motor de voz local no está instalado.",
                solution=(
                    "Instalá piper-tts: pip install piper-tts  y "
                    "descargá una voz: python scripts/download_voice.py es_AR-daniela-high"
                ),
            )

        audio_dir = project_dir(project_id) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"voice_{uuid4().hex[:10]}.wav"
        out_path = audio_dir / out_name

        provider.synthesize(
            text=req.text.strip(),
            out_path=out_path,
            voice_id=req.voice_id,
            speed=req.speed,
        )

        if not out_path.exists() or out_path.stat().st_size == 0:
            raise ValidationError(
                message="No se pudo generar el audio.",
            )

        # URL para reproducir vía /files
        rel = out_path.resolve().relative_to(settings.BASE_DIR.resolve())
        audio_url = "/" + str(rel).replace("\\", "/")

        duration = None
        if isinstance(provider, LocalPiperTTS):
            duration = LocalPiperTTS.probe_duration(out_path)

        log.info(
            "Voz sintetizada para %s: %s (%d bytes)",
            project_id, out_name, out_path.stat().st_size,
        )
        try:
            proj = await self.projects.get_project(project_id)
            proj.voice_track = audio_url  # guardamos la URL relativa
            await self.projects.repo.update(proj)
        except Exception:
            log.exception("No se pudo asociar la voz al proyecto")
        
        return SynthesizeResponse(
            audio_path=str(out_path),
            audio_url=audio_url,
            voice_id=req.voice_id or "",
            duration=duration,
            size_bytes=out_path.stat().st_size,
        )