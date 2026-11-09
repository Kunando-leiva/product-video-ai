"""Pipeline de render: traduce la timeline a operaciones FFmpeg.

Regla 43: la IA (o el usuario) produce datos estructurados.
El pipeline los traduce a operaciones del FFmpegEngine.

Regla 57: la IA NUNCA ejecuta comandos. Aquí solo se ejecuta un
pipeline validado por tipos.
"""
import logging
import shutil
from pathlib import Path
from typing import Callable, Optional

from app.core import ffmpeg
from app.core.errors import ValidationError
from app.models.db_models import Media, TimelineItem
from app.video.effects import build_vf
from app.video.ffmpeg_runner import run_ffmpeg


log = logging.getLogger("app.video.render")


FORMAT_SIZES: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "16:9": (1920, 1080),
}


ProgressCb = Callable[[float], None]


class RenderPipeline:
    def __init__(
        self,
        work_dir: Path,
        output_path: Path,
        fmt: str = "9:16",
        fps: int = 30,
        voice_path: Optional[Path] = None,
        music_path: Optional[Path] = None,
        voice_volume: float = 1.0,
        music_volume: float = 0.15,
        on_progress: Optional[ProgressCb] = None,
    ) -> None:
        if fmt not in FORMAT_SIZES:
            raise ValidationError(
                message=f"Formato inválido: {fmt}",
                solution=f"Elegí uno de: {', '.join(FORMAT_SIZES)}",
            )
        self.work_dir = work_dir
        self.output_path = output_path
        self.width, self.height = FORMAT_SIZES[fmt]
        self.fps = fps
        self.voice_path = voice_path
        self.music_path = music_path
        self.voice_volume = voice_volume
        self.music_volume = music_volume
        self.on_progress = on_progress

    # ------------------------------------------------------------------

    def _emit(self, progress: float) -> None:
        if self.on_progress:
            try:
                self.on_progress(max(0.0, min(1.0, progress)))
            except Exception:  # pragma: no cover
                log.exception("on_progress callback falló")

    # ------------------------------------------------------------------

    def render(
        self,
        items: list[TimelineItem],
        media_by_id: dict[str, Media],
    ) -> Path:
        ffmpeg.require_ffmpeg()

        if not items:
            raise ValidationError(
                message="La timeline está vacía.",
                solution="Agregá al menos un clip antes de renderizar.",
            )

        has_audio = bool(
            (self.voice_path and self.voice_path.exists())
            or (self.music_path and self.music_path.exists())
        )

        # Reparto de progreso
        p_clips_end = 0.75
        p_concat_end = 0.90

        self.work_dir.mkdir(parents=True, exist_ok=True)
        for f in self.work_dir.glob("clip_*.mp4"):
            f.unlink(missing_ok=True)
        for f in self.work_dir.glob("silent.mp4"):
            f.unlink(missing_ok=True)
        for f in self.work_dir.glob("with_audio.mp4"):
            f.unlink(missing_ok=True)

        total = len(items)
        rendered: list[Path] = []

        for idx, item in enumerate(items):
            m = media_by_id.get(item.media_id) if item.media_id else None
            if m is None:
                log.warning("Item %s sin media, se omite", item.id)
                continue
            clip = self.work_dir / f"clip_{idx:03d}.mp4"
            self._render_clip(item, m, clip)
            rendered.append(clip)
            self._emit(p_clips_end * (idx + 1) / max(total, 1))

        if not rendered:
            raise ValidationError(
                message="Ningún clip pudo renderizarse.",
                solution="Verificá que los archivos del proyecto sigan en disco.",
            )

        # Concat (sin audio)
        list_file = self.work_dir / "concat_list.txt"
        list_file.write_text(
            "\n".join(f"file '{c.name}'" for c in rendered),
            encoding="utf-8",
        )
        silent = self.work_dir / "silent.mp4"
        run_ffmpeg(
            [
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(silent),
            ]
        )
        self._emit(p_concat_end)

        # Si no hay audio, el silent es el final
        if not has_audio:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(silent), str(self.output_path))
            self._emit(1.0)
            log.info("Render OK (sin audio): %s", self.output_path)
            return self.output_path

        # Audio: mezclar voz + música sobre el silent
        with_audio = self.work_dir / "with_audio.mp4"
        self._mix_audio(silent, with_audio)
        self._emit(0.98)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(with_audio), str(self.output_path))
        self._emit(1.0)
        log.info("Render OK (con audio): %s", self.output_path)
        return self.output_path

    # ------------------------------------------------------------------

    def _render_clip(
        self, item: TimelineItem, media: Media, out_path: Path
    ) -> None:
        src = Path(media.path)
        if not src.exists():
            raise ValidationError(
                message=f"El archivo ya no existe: {media.original_name}",
                solution="Volvé a subirlo al proyecto.",
            )

        vf = build_vf(
            effect=item.effect,
            duration=item.duration,
            width=self.width,
            height=self.height,
            fps=self.fps,
        )

        args = ["-y"]
        if media.type == "image":
            args += ["-loop", "1", "-t", f"{item.duration:.3f}", "-i", str(src)]
        elif media.type == "video":
            args += ["-i", str(src), "-t", f"{item.duration:.3f}"]
        else:
            raise ValidationError(
                message=f"Tipo de media no soportado para video: {media.type}",
                solution="Usá imágenes o videos en la timeline.",
            )

        args += [
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-an",
            str(out_path),
        ]
        run_ffmpeg(args, timeout=300)

    # ------------------------------------------------------------------

    def _mix_audio(self, silent_video: Path, out_path: Path) -> None:
        """Mezcla voz + música sobre el video (Regla 17: música al 10–20%)."""
        voice = self.voice_path if (self.voice_path and self.voice_path.exists()) else None
        music = self.music_path if (self.music_path and self.music_path.exists()) else None

        if voice and music:
            # Voz al 100%, música al X% + loop de música para cubrir el video
            filter_complex = (
                f"[1:a]volume={self.voice_volume}[voice];"
                f"[2:a]volume={self.music_volume}[music];"
                f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )
            run_ffmpeg(
                [
                    "-y",
                    "-i", str(silent_video),
                    "-i", str(voice),
                    "-stream_loop", "-1", "-i", str(music),
                    "-filter_complex", filter_complex,
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    str(out_path),
                ],
                timeout=600,
            )
        elif voice:
            # Solo voz
            run_ffmpeg(
                [
                    "-y",
                    "-i", str(silent_video),
                    "-i", str(voice),
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-filter:a", f"volume={self.voice_volume}",
                    "-shortest",
                    str(out_path),
                ],
                timeout=600,
            )
        elif music:
            # Solo música (con loop para cubrir el video)
            run_ffmpeg(
                [
                    "-y",
                    "-i", str(silent_video),
                    "-stream_loop", "-1", "-i", str(music),
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-filter:a", f"volume={self.music_volume}",
                    "-shortest",
                    str(out_path),
                ],
                timeout=600,
            )
        else:  # pragma: no cover — no debería llegar
            shutil.copy(silent_video, out_path)